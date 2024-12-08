from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm import joinedload

from db.database import get_db
from db.models import User, Chat, Team, Project, Stack
from db.queries import get_chat_for_user
from agents.prompts import name_chat
from sandbox.sandbox import DevSandbox
from config import CREDITS_CHAT_COST
from schemas.models import ChatCreate, ChatUpdate, ChatResponse
from routers.auth import get_current_user_from_token

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=List[ChatResponse])
async def get_user_chats(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .options(joinedload(Chat.messages), joinedload(Chat.project))
        .all()
    )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .options(joinedload(Chat.messages), joinedload(Chat.project))
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.messages:
        chat.messages = sorted(chat.messages, key=lambda x: x.created_at)
    return chat


@router.post("", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    team = (
        db.query(Team)
        .filter(Team.id == chat.team_id, Team.members.any(user_id=current_user.id))
        .first()
    )
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    team_id = team.id

    if chat.stack_id is None:
        # TODO: AI
        stack = db.query(Stack).filter(Stack.title == "Next.js Shadcn").first()
    else:
        stack = db.query(Stack).filter(Stack.id == chat.stack_id).first()
        if stack is None:
            raise HTTPException(status_code=404, detail="Stack not found")

    project_name, project_description, chat_name = await name_chat(chat.seed_prompt)

    if chat.project_id is None:
        project = Project(
            name=project_name,
            description=project_description,
            custom_instructions="",
            user_id=current_user.id,
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
        name=chat_name,
        project_id=project_id,
        user_id=current_user.id,
    )

    if team.credits < CREDITS_CHAT_COST:
        raise HTTPException(
            status_code=402,
            detail=f"Team does not have enough credits. Required: {CREDITS_CHAT_COST}, Available: {team.credits}",
        )

    team.credits -= CREDITS_CHAT_COST

    try:
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return new_chat


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    chat = get_chat_for_user(db, chat_id, current_user)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    project_id = chat.project_id
    db.delete(chat)

    remaining_chats = (
        db.query(Chat).filter(Chat.project_id == project_id, Chat.id != chat_id).first()
    )
    project_deleted = None
    if not remaining_chats:
        project_deleted = db.query(Project).filter(Project.id == project_id).first()
        if project_deleted:
            db.delete(project_deleted)

    db.commit()

    if project_deleted:
        await DevSandbox.destroy_project_resources(project_deleted)

    return {"message": "Chat deleted successfully"}


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    chat = get_chat_for_user(db, chat_id, current_user)
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
