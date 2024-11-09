from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
from modal import Sandbox, forward
import json
import random
from datetime import datetime

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


@app.post("/api/auth/create", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user or return existing user with the given username"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        # If user exists, return the existing user
        return existing_user

    # Create new user
    new_user = User(username=user.username)
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return new_user


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user(username: str, db: Session = Depends(get_db)):
    """Get current user by username"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/projects/{username}", response_model=List[ProjectResponse])
async def get_user_projects(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.projects


@app.post("/projects/create", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate, username: str, db: Session = Depends(get_db)
):
    # Find user
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create project
    new_project = Project(
        name=project.name, description=project.description, owner_id=user.id
    )

    db.add(new_project)
    try:
        db.commit()
        db.refresh(new_project)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return new_project


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Generate a response
            response = {
                "type": "assistant",
                "content": random.choice(SAMPLE_RESPONSES),
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_json(response)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
