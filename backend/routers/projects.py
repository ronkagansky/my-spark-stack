from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_

from db.database import get_db
from db.models import User, Project, Team, TeamMember
from schemas.models import (
    ProjectResponse,
    ProjectFileContentResponse,
)
from sandbox.sandbox import DevSandbox
from routers.auth import get_current_user_from_token

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(Project)
        .join(Team, Project.team_id == Team.id)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .filter(
            or_(
                Project.user_id == current_user.id,  # User owns the project
                and_(
                    TeamMember.user_id == current_user.id,  # User is team member
                    TeamMember.team_id == Project.team_id,
                ),
            ),
        )
        .all()
    )
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .join(Team, Project.team_id == Team.id)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .filter(
            Project.id == project_id,
            or_(
                Project.user_id == current_user.id,  # User owns the project
                and_(
                    TeamMember.user_id == current_user.id,  # User is team member
                    TeamMember.team_id == Project.team_id,
                ),
            ),
        )
        .first()
    )

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/file/{path:path}", response_model=ProjectFileContentResponse)
async def get_project_file(
    project_id: int,
    path: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = await get_project(project_id, current_user, db)
    sandbox = await DevSandbox.get_or_create(project.id)
    return ProjectFileContentResponse(
        path=path, content=await sandbox.read_file_contents(path)
    )
