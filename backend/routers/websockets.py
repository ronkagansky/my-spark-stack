from fastapi import APIRouter, WebSocket, WebSocketException
from typing import Dict, List
from datetime import datetime
from openai import OpenAI
from enum import Enum
from asyncio import create_task
from pydantic import BaseModel
import os
import aiohttp
import asyncio


class SandboxStatus(str, Enum):
    BUILDING = "CREATING"
    READY = "READY"


class SandboxStatusResponse(BaseModel):
    for_type: str = "sandbox_status"
    status: SandboxStatus
    tunnels: Dict[int, str]


from sandbox.sandbox import DevSandbox
from db.database import get_db
from db.models import Project

router = APIRouter(tags=["websockets"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    sandbox_task = create_task(create_sandbox(websocket, project_id))

    try:
        while True:
            data = await websocket.receive_text()

            # Create streaming chat completion
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # or your preferred model
                messages=[{"role": "user", "content": data}],
                stream=True,
            )

            # Stream the response chunks
            collected_content = []
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    collected_content.append(content)

                    # Send each chunk as it arrives
                    chunk_response = {
                        "type": "assistant",
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat(),
                        "project_id": project_id,
                        "is_chunk": True,
                    }

                    # Send chunk to all connections for this project
                    for connection in project_connections[project_id]:
                        await connection.send_json(chunk_response)

            # Send final complete message
            final_response = {
                "type": "assistant",
                "content": "".join(collected_content),
                "timestamp": datetime.utcnow().isoformat(),
                "project_id": project_id,
                "is_chunk": False,
            }

            # Send final message to all connections
            for connection in project_connections[project_id]:
                await connection.send_json(final_response)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        sandbox_task.cancel()
        project_connections[project_id].remove(websocket)
        if not project_connections[project_id]:
            del project_connections[project_id]
        await websocket.close()


async def _wait_for_up(url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status < 500  # Accept any non-server error response
    except:
        return False


async def create_sandbox(websocket: WebSocket, project_id: int):
    await websocket.send_json(
        SandboxStatusResponse(status=SandboxStatus.BUILDING, tunnels={}).model_dump()
    )

    sandbox = await DevSandbox.get_or_create(project_id)

    while True:
        tunnels = await sandbox.sb.tunnels.aio()
        tunnel_url = tunnels[3000].url
        if await _wait_for_up(tunnel_url):
            break

        await asyncio.sleep(3)

    tunnels = await sandbox.sb.tunnels.aio()
    await websocket.send_json(
        SandboxStatusResponse(
            status=SandboxStatus.READY,
            tunnels={port: tunnel.url for port, tunnel in tunnels.items()},
        ).model_dump()
    )
