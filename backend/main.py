from fastapi import FastAPI, HTTPException, Depends, WebSocket, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
from modal import Sandbox, forward
import json
import random
from datetime import datetime, timedelta
import secrets
from jose import jwt, JWTError
from openai import OpenAI

from db.database import get_db, init_db
from db.models import User, Project

app = FastAPI()


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development frontend
        "http://localhost:8000",  # Production
        "https://*.up.railway.app",  # Railway domains
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add these sample responses
SAMPLE_RESPONSES = [
    "I've analyzed the code structure. The main components seem well-organized. What specific part would you like me to explain?",
    "That's an interesting question about the project. Let me break it down for you...",
    "I can help you modify the code. What changes would you like to make?",
    "The current implementation follows React best practices. We could enhance it by...",
    "Based on your question, I think we should focus on improving the user experience by...",
]

# Add these constants at the top with other imports
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
API_KEY_HEADER = APIKeyHeader(name="Authorization")

# Add a dictionary to store project websocket connections
project_connections: Dict[int, List[WebSocket]] = {}

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Add this function after the imports
async def get_current_user_from_token(
    token: str = Security(API_KEY_HEADER), db: Session = Depends(get_db)
):
    try:
        # Remove 'Bearer ' prefix if present
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class UserCreate(BaseModel):
    username: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int

    class Config:
        from_attributes = True


# Add this new response model after the other model definitions
class AuthResponse(BaseModel):
    user: UserResponse
    token: str

    class Config:
        from_attributes = True


@app.post("/api/auth/create", response_model=AuthResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user or return existing user with the given username"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        # If user exists, generate new token and return
        token = jwt.encode(
            {
                "sub": existing_user.username,
                "exp": datetime.utcnow() + timedelta(days=30),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        return AuthResponse(user=existing_user, token=token)

    # Create new user
    new_user = User(username=user.username)
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        # Generate token for new user
        token = jwt.encode(
            {"sub": new_user.username, "exp": datetime.utcnow() + timedelta(days=30)},
            SECRET_KEY,
            algorithm="HS256",
        )
        return AuthResponse(user=new_user, token=token)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user_from_token)):
    return current_user


@app.get("/api/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Get projects for the authenticated user"""
    return current_user.projects


@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    # Create project using the authenticated user
    new_project = Project(
        name=project.name, description=project.description, owner_id=current_user.id
    )

    db.add(new_project)
    try:
        db.commit()
        db.refresh(new_project)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return new_project


@app.websocket("/api/ws/chat/{project_id}")
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


if __name__ == "__main__":
    init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
