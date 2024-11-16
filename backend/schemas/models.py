from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    username: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    name: str
    description: Optional[str] = None
    stack_id: Optional[str] = None
    project_id: Optional[int] = None
    team_id: Optional[int] = None


class ChatResponse(BaseModel):
    id: int
    name: str


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class ProjectFileContentResponse(BaseModel):
    path: str
    content: str


class AuthResponse(BaseModel):
    user: UserResponse
    token: str

    class Config:
        from_attributes = True


class ChatUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class StackResponse(BaseModel):
    id: int
    title: str
    description: str
    prompt: str
    from_registry: str
    sandbox_init_cmd: str
    sandbox_start_cmd: str

    class Config:
        from_attributes = True
