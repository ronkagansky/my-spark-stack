from fastapi import APIRouter, WebSocket, WebSocketException, WebSocketDisconnect
from typing import Dict, List, Optional
from enum import Enum
from asyncio import create_task, Lock
from pydantic import BaseModel
import datetime
import asyncio
import traceback

from sandbox.sandbox import DevSandbox, SandboxNotReadyException
from agents.agent import Agent, ChatMessage
from agents.diff import parse_file_changes
from db.database import get_db
from db.models import Project, Message as DbChatMessage, Stack
from db.queries import get_chat_for_user
from agents.prompts import write_commit_message
from routers.auth import get_current_user_from_token
from sqlalchemy.orm import Session


class SandboxStatus(str, Enum):
    OFFLINE = "OFFLINE"
    BUILDING = "BUILDING"
    BUILDING_WAITING = "BUILDING_WAITING"
    READY = "READY"
    WORKING = "WORKING"
    WORKING_APPLYING = "WORKING_APPLYING"


class ProjectStatusResponse(BaseModel):
    for_type: str = "status"
    project_id: int
    sandbox_status: SandboxStatus
    tunnels: Dict[int, str]
    file_paths: Optional[List[str]] = None


class ChatUpdateResponse(BaseModel):
    for_type: str = "chat_update"
    chat_id: int
    message: ChatMessage
    follow_ups: Optional[List[str]] = None
    navigate_to: Optional[str] = None


class ChatChunkResponse(BaseModel):
    for_type: str = "chat_chunk"
    role: str
    content: str
    thinking_content: str


def _message_to_db_message(message: ChatMessage, chat_id: int) -> DbChatMessage:
    return DbChatMessage(
        role=message.role,
        content=message.content,
        images=message.images,
        chat_id=chat_id,
    )


def _db_message_to_message(db_message: DbChatMessage) -> ChatMessage:
    return ChatMessage(
        id=db_message.id,
        role=db_message.role,
        content=db_message.content,
        images=db_message.images,
    )


router = APIRouter(tags=["websockets"])


async def _apply_file_changes(agent: Agent, total_content: str):
    if agent.sandbox:
        changes = await parse_file_changes(agent.sandbox, total_content)
        if len(changes) > 0:
            commit_message = await write_commit_message(total_content)
            print("Applying Changes", [f.path for f in changes], repr(commit_message))
            await agent.sandbox.write_file_contents_and_commit(
                [(change.path, change.content) for change in changes], commit_message
            )


class ProjectManager:
    def __init__(self, db: Session, project_id: int):
        self.db = db
        self.project_id = project_id
        self.chat_sockets: Dict[int, List[WebSocket]] = {}
        self.chat_agents: Dict[int, Agent] = {}
        self.lock: Lock = Lock()
        self.sandbox_status = SandboxStatus.OFFLINE
        self.sandbox = None
        self.sandbox_file_paths: Optional[List[str]] = None
        self.tunnels = {}
        self.last_activity = datetime.datetime.now()

    def is_inactive(self, timeout_minutes: int = 30) -> bool:
        return len(self.chat_sockets) == 0 and (
            datetime.datetime.now() - self.last_activity
        ) > datetime.timedelta(minutes=timeout_minutes)

    async def kill(self):
        self.sandbox_status = SandboxStatus.BUILDING
        await self.emit_project(await self._get_project_status())

        # Close all websockets
        close_tasks = []
        for sockets in self.chat_sockets.values():
            for socket in sockets:
                try:
                    close_tasks.append(socket.close())
                except Exception:
                    pass
        if close_tasks:
            await asyncio.gather(*close_tasks)

        # Clear socket and agent dictionaries
        self.chat_sockets.clear()
        self.chat_agents.clear()

        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if project and project.modal_volume_label:
            await DevSandbox.terminate_project_resources(project)

    async def _manage_sandbox_task(self):
        print(f"Managing sandbox for project {self.project_id}...")
        self.sandbox_status = SandboxStatus.BUILDING
        await self.emit_project(await self._get_project_status())
        while self.sandbox is None:
            try:
                self.sandbox = await DevSandbox.get_or_create(self.project_id)
            except SandboxNotReadyException:
                self.sandbox_status = SandboxStatus.BUILDING_WAITING
                await self.emit_project(await self._get_project_status())
            await asyncio.sleep(30)
        await self.sandbox.wait_for_up()
        self.sandbox_status = SandboxStatus.READY
        tunnels = await self.sandbox.sb.tunnels.aio()
        self.tunnels = {port: tunnel.url for port, tunnel in tunnels.items()}
        self.sandbox_file_paths = await self.sandbox.get_file_paths()
        await self.emit_project(await self._get_project_status())
        for agent in self.chat_agents.values():
            agent.sandbox = self.sandbox

    async def _try_manage_sandbox(self):
        while True:
            try:
                await self._manage_sandbox_task()
                break
            except Exception as e:
                print(f"Error managing sandbox {e}\n{traceback.format_exc()}")
            await asyncio.sleep(30)

    def start(self):
        create_task(self._try_manage_sandbox())

    async def _get_project_status(self):
        return ProjectStatusResponse(
            project_id=self.project_id,
            sandbox_status=self.sandbox_status,
            tunnels=self.tunnels,
            file_paths=self.sandbox_file_paths,
        )

    async def add_chat_socket(self, chat_id: int, websocket: WebSocket):
        self.last_activity = datetime.datetime.now()
        if chat_id not in self.chat_sockets:
            project = (
                self.db.query(Project).filter(Project.id == self.project_id).first()
            )
            stack = self.db.query(Stack).filter(Stack.id == project.stack_id).first()
            agent = Agent(project, stack)
            agent.sandbox = self.sandbox
            self.chat_agents[chat_id] = agent
            self.chat_sockets[chat_id] = []
        self.chat_sockets[chat_id].append(websocket)
        await self.emit_project(await self._get_project_status())

    def remove_chat_socket(self, chat_id: int, websocket: WebSocket):
        self.chat_sockets[chat_id].remove(websocket)
        if len(self.chat_sockets[chat_id]) == 0:
            del self.chat_sockets[chat_id]
            del self.chat_agents[chat_id]

    async def _handle_chat_message(self, chat_id: int, message: ChatMessage):
        self.sandbox_status = SandboxStatus.WORKING
        await self.emit_project(await self._get_project_status())

        db_message = _message_to_db_message(message, chat_id)
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        await self.emit_chat(
            chat_id,
            ChatUpdateResponse(
                chat_id=chat_id, message=_db_message_to_message(db_message)
            ),
        )

        agent = self.chat_agents[chat_id]
        db_messages = (
            self.db.query(DbChatMessage)
            .filter(DbChatMessage.chat_id == chat_id)
            .order_by(DbChatMessage.created_at)
            .all()
        )
        messages = [_db_message_to_message(m) for m in db_messages]
        total_content = ""
        async for partial_message in agent.step(messages, self.sandbox_file_paths):
            total_content += partial_message.delta_content
            await self.emit_chat(
                chat_id,
                ChatChunkResponse(
                    role="assistant",
                    content=partial_message.delta_content,
                    thinking_content=partial_message.delta_thinking_content,
                ),
            )

        resp_message = ChatMessage(role="assistant", content=total_content)
        db_resp_message = _message_to_db_message(resp_message, chat_id)
        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        project.modal_sandbox_last_used_at = datetime.datetime.now()
        self.db.add(db_resp_message)
        self.db.commit()

        self.sandbox_status = SandboxStatus.WORKING_APPLYING
        _, _, follow_ups = await asyncio.gather(
            self.emit_project(await self._get_project_status()),
            _apply_file_changes(agent, total_content),
            agent.suggest_follow_ups(messages + [resp_message]),
        )

        await self.emit_chat(
            chat_id,
            ChatUpdateResponse(
                chat_id=chat_id,
                message=_db_message_to_message(db_resp_message),
                follow_ups=follow_ups,
                navigate_to=agent.working_page,
            ),
        )

        self.sandbox_status = SandboxStatus.READY
        self.sandbox_file_paths = await self.sandbox.get_file_paths()
        await self.emit_project(await self._get_project_status())

    async def _try_handle_chat_message(self, chat_id: int, message: ChatMessage):
        try:
            await self._handle_chat_message(chat_id, message)
        except Exception as e:
            print(
                f"Error in chat message: {str(e)}\nTraceback:\n{traceback.format_exc()}"
            )
            self.sandbox_status = SandboxStatus.READY
            await self.emit_project(await self._get_project_status())

    async def on_chat_message(self, chat_id: int, message: ChatMessage):
        self.last_activity = datetime.datetime.now()
        if not await self.lock.acquire():
            return
        await self._try_handle_chat_message(chat_id, message)
        self.lock.release()

    async def emit_project(self, data: BaseModel):
        await asyncio.gather(
            *[self.emit_chat(chat_id, data) for chat_id in self.chat_sockets]
        )

    async def emit_chat(self, chat_id: int, data: BaseModel):
        if chat_id not in self.chat_sockets:
            return
        sockets = list(self.chat_sockets[chat_id])

        async def _try_send(socket: WebSocket):
            try:
                await socket.send_json(data.model_dump())
            except Exception:
                try:
                    self.chat_sockets[chat_id].remove(socket)
                except ValueError:
                    pass

        await asyncio.gather(*[_try_send(socket) for socket in sockets])


project_managers: Dict[int, ProjectManager] = {}


@router.websocket("/api/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    db = next(get_db())
    token = websocket.query_params.get("token")
    current_user = await get_current_user_from_token(token, db)
    chat = get_chat_for_user(db, chat_id, current_user)
    if chat is None:
        raise WebSocketException(code=404, reason="Chat not found")

    project = chat.project
    if project is None:
        raise WebSocketException(code=404, reason="Project not found")

    if project.id not in project_managers:
        pm = ProjectManager(db, project.id)
        pm.start()
        project_managers[project.id] = pm
    else:
        pm = project_managers[project.id]

    await websocket.accept()
    await pm.add_chat_socket(chat_id, websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = ChatMessage.model_validate_json(raw_data)
            create_task(pm.on_chat_message(chat_id, data))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"websocket loop error: {e}\n{traceback.format_exc()}")
    finally:
        pm.remove_chat_socket(chat_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
        db.close()
