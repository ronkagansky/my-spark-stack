from fastapi import APIRouter, WebSocket
from typing import Dict, List
from datetime import datetime
from openai import OpenAI
import os


router = APIRouter(tags=["websockets"])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Store project websocket connections
project_connections: Dict[int, List[WebSocket]] = {}


@router.websocket("/api/ws/project-chat/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    await websocket.accept()

    # Add connection to project's connection list
    if project_id not in project_connections:
        project_connections[project_id] = []
    project_connections[project_id].append(websocket)

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
        # Remove connection from project's connection list
        project_connections[project_id].remove(websocket)
        if not project_connections[project_id]:
            del project_connections[project_id]
        await websocket.close()
