from fastapi import APIRouter, WebSocket, WebSocketException
from typing import Dict, List
from enum import Enum
from asyncio import create_task
from pydantic import BaseModel

from sandbox.sandbox import DevSandbox
from agents.agent import Agent, ChatMessage, parse_file_changes
from db.database import get_db
from db.models import Project


class SandboxStatus(str, Enum):
    BUILDING = "CREATING"
    READY = "READY"


class SandboxStatusResponse(BaseModel):
    for_type: str = "sandbox_status"
    status: SandboxStatus
    tunnels: Dict[int, str]


class SandboxFileTreeResponse(BaseModel):
    for_type: str = "sandbox_file_tree"
    paths: List[str]


class ChatChunkResponse(BaseModel):
    for_type: str = "chat_chunk"
    content: str


class ChatRequest(BaseModel):
    chat: List[ChatMessage]


router = APIRouter(tags=["websockets"])

# Store project websocket connections
project_connections: Dict[int, List[WebSocket]] = {}


@router.websocket("/api/ws/project-chat/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    db = next(get_db())
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise WebSocketException(code=404, reason="Project not found")

    await websocket.accept()

    # Add connection to project's connection list
    if project_id not in project_connections:
        project_connections[project_id] = []
    project_connections[project_id].append(websocket)

    agent = Agent(project)
    sandbox_task = create_task(create_sandbox(websocket, agent, project_id))

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = ChatRequest.model_validate_json(raw_data)

            total_content = ""
            async for partial_message in agent.step(data.chat):
                total_content += partial_message.delta_content
                response = ChatChunkResponse(content=partial_message.delta_content)
                for connection in project_connections[project_id]:
                    await connection.send_json(response.model_dump())

            if agent.sandbox:
                changes = parse_file_changes(agent.sandbox, total_content)
                print("applying changes", changes)
                try:
                    await agent.sandbox.write_file_contents(
                        [(change.path, change.content) for change in changes]
                    )
                except Exception as e:
                    print("error applying changes", e)

            await websocket.send_json(
                SandboxFileTreeResponse(
                    paths=await agent.sandbox.get_file_paths()
                ).model_dump()
            )

    except Exception as e:
        # TODO: Handle error
        pass
    finally:
        sandbox_task.cancel()
        project_connections[project_id].remove(websocket)
        if not project_connections[project_id]:
            del project_connections[project_id]
        await websocket.close()


async def create_sandbox(websocket: WebSocket, agent: Agent, project_id: int):
    await websocket.send_json(
        SandboxStatusResponse(status=SandboxStatus.BUILDING, tunnels={}).model_dump()
    )

    sandbox = await DevSandbox.get_or_create(project_id)
    agent.set_sandbox(sandbox)
    await sandbox.wait_for_up()

    paths = await sandbox.get_file_paths()
    await websocket.send_json(SandboxFileTreeResponse(paths=paths).model_dump())

    tunnels = await sandbox.sb.tunnels.aio()
    await websocket.send_json(
        SandboxStatusResponse(
            status=SandboxStatus.READY,
            tunnels={port: tunnel.url for port, tunnel in tunnels.items()},
        ).model_dump()
    )
