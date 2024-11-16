from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm import joinedload

from db.database import get_db
from db.models import User, Chat, Team, Project, Stack
from schemas.models import ChatCreate, ChatUpdate, ChatResponse
from sandbox.sandbox import DevSandbox
from routers.auth import get_current_user_from_token

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=List[ChatResponse])
async def get_user_chats(
    current_user: User = Depends(get_current_user_from_token),
):
    return current_user.chats


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.owner_id == current_user.id)
        .options(joinedload(Chat.chat_messages))
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if chat.team_id is None:
        team = db.query(Team).filter(Team.members.any(id=current_user.id)).first()
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")
        team_id = team.id
    else:
        team = (
            db.query(Team)
            .filter(Team.id == chat.team_id, Team.members.any(id=current_user.id))
            .first()
        )
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")
        team_id = team.id

    if chat.stack_id is None:
        # TODO: AI
        stack = db.query(Stack).first()
    else:
        stack = db.query(Stack).filter(Stack.id == chat.stack_id).first()
        if stack is None:
            raise HTTPException(status_code=404, detail="Stack not found")

    if chat.project_id is None:
        project = Project(
            name=chat.name,
            description=chat.description,
            owner_id=current_user.id,
            team_id=team_id,
            stack_id=stack.id,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id
    else:
        project = (
            db.query(Project)
            .filter(
                Project.id == chat.project_id,
                ((Project.user_id == current_user.id) | (Project.team_id == team_id)),
            )
            .first()
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        project_id = project.id

    new_chat = Chat(
        name=chat.name,
        description=chat.description,
        project_id=project_id,
    )

    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return new_chat


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.owner_id == current_user.id)
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Project not found")

    await DevSandbox.delete(chat.id)

    db.delete(chat)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Project deleted successfully"}


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.owner_id == current_user.id)
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    for field, value in chat_update.dict(exclude_unset=True).items():
        setattr(chat, field, value)

    try:
        db.commit()
        db.refresh(chat)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return chat
