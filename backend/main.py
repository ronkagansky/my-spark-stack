from fastapi import FastAPI, HTTPException, Depends, WebSocket, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
from modal import Sandbox, forward
import json
import random
from datetime import datetime, timedelta
import secrets
from jose import jwt, JWTError

from db.database import get_db, init_db
from db.models import User, Project

app = FastAPI()

# # Mount Next.js static files
# app.mount("/_next", StaticFiles(directory="../frontend/.next"), name="next_static")
# app.mount("/static", StaticFiles(directory="../frontend/public"), name="public_static")


# # Serve Next.js frontend - add this before other routes
# @app.get("/{full_path:path}")
# async def serve_frontend(full_path: str):
#     # API routes should not be handled by frontend
#     if full_path.startswith("api/") or full_path.startswith("ws/"):
#         raise HTTPException(status_code=404, detail="Not found")

#     # Serve the Next.js index.html for all other routes
#     return FileResponse("frontend/.next/server/pages/index.html")


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


@app.websocket("/api/ws/chat")
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
