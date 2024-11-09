from pydantic import BaseModel
from typing import Optional


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


class AuthResponse(BaseModel):
    user: UserResponse
    token: str

    class Config:
        from_attributes = True
