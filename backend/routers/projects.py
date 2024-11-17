from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import and_

from db.database import get_db
from db.models import User, Project, Team, TeamMember, Chat
from db.queries import get_project_for_user
from schemas.models import (
    ProjectResponse,
    ProjectFileContentResponse,
    ProjectGitLogResponse,
    ProjectUpdate,
    ChatResponse,
)
from sandbox.sandbox import DevSandbox
from routers.auth import get_current_user_from_token

router = APIRouter(prefix="/api/teams/{team_id}/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
async def get_user_projects(
    team_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(Project)
        .join(Team, Project.team_id == Team.id)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .filter(
            and_(
                Team.id == team_id,
                TeamMember.user_id == current_user.id,
                TeamMember.team_id == Project.team_id,
            ),
        )
        .all()
    )
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    team_id: int,
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = project_data.name
    project.description = project_data.description
    project.custom_instructions = project_data.custom_instructions
    db.commit()
    return project


@router.get("/{project_id}/file/{path:path}", response_model=ProjectFileContentResponse)
async def get_project_file(
    team_id: int,
    project_id: int,
    path: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = await get_project(team_id, project_id, current_user, db)
    sandbox = await DevSandbox.get_or_create(project.id)
    return ProjectFileContentResponse(
        path=path, content=await sandbox.read_file_contents(path)
    )


@router.get("/{project_id}/git-log", response_model=ProjectGitLogResponse)
async def get_project_git_log(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = await get_project(team_id, project_id, current_user, db)
    sandbox = await DevSandbox.get_or_create(project.id)
    content = await sandbox.run_command('git log --pretty="%h|%s|%aN|%aE|%aD" -n 10')
    return ProjectGitLogResponse.from_content(content)


@router.get("/{project_id}/chats", response_model=List[ChatResponse])
async def get_project_chats(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    chats = (
        db.query(Chat)
        .filter(
            and_(
                Chat.project_id == project_id,
                Chat.user_id == current_user.id,
            )
        )
        .order_by(Chat.created_at.desc())
        .all()
    )
    return chats


@router.delete("/{project_id}")
async def delete_project(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    chats = db.query(Chat).filter(Chat.project_id == project_id).all()
    for chat in chats:
        db.delete(chat)

    db.commit()

    await DevSandbox.destroy_project_resources(project)

    return {"message": "Project deleted successfully"}
