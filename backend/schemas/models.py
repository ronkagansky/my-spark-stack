from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    username: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    credits: int

    class Config:
        from_attributes = True


class ImageUploadSignURL(BaseModel):
    content_type: str


class ChatCreate(BaseModel):
    name: str
    stack_id: Optional[int] = None
    project_id: Optional[int] = None
    team_id: int
    seed_prompt: Optional[str] = None


class MessageResponse(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    description: Optional[str] = None
    custom_instructions: Optional[str] = None

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: Optional[List[MessageResponse]] = None
    project: Optional[ProjectResponse] = None

    class Config:
        from_attributes = True


class ProjectFileContentResponse(BaseModel):
    path: str
    content: str


class GitLogEntry(BaseModel):
    hash: str
    message: str
    author: str
    email: str
    date: str

    @classmethod
    def from_line(cls, line: str):
        hash, message, author, email, date = line.split("|")
        return cls(hash=hash, message=message, author=author, email=email, date=date)


class ProjectGitLogResponse(BaseModel):
    lines: List[GitLogEntry]

    @classmethod
    def from_content(cls, content: str):
        return cls(
            lines=[
                GitLogEntry.from_line(line)
                for line in content.split("\n")
                if line.count("|") == 4
            ]
        )


class AuthResponse(BaseModel):
    user: UserResponse
    token: str

    class Config:
        from_attributes = True


class ChatUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    custom_instructions: Optional[str] = None


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


class TeamInviteResponse(BaseModel):
    invite_link: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None
