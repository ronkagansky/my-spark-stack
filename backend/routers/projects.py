from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm import joinedload

from db.database import get_db
from db.models import User, Project
from schemas.models import (
    ProjectCreate,
    ProjectResponse,
    ProjectFileContentResponse,
    ProjectUpdate,
)
from sandbox.sandbox import DevSandbox
from routers.auth import get_current_user_from_token

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user_from_token),
):
    return current_user.projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .options(joinedload(Project.chat_messages))
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


@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
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


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Project deleted successfully"}


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in project_update.dict(exclude_unset=True).items():
        setattr(project, field, value)

    try:
        db.commit()
        db.refresh(project)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return project
