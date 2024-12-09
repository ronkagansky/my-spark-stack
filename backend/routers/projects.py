from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import and_
from sse_starlette.sse import EventSourceResponse
import json
import re

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
    content = await DevSandbox.get_project_file_contents(project, path)
    return ProjectFileContentResponse(path=path, content=content)


@router.get("/{project_id}/git-log", response_model=ProjectGitLogResponse)
async def get_project_git_log(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = await get_project(team_id, project_id, current_user, db)
    content = await DevSandbox.get_project_file_contents(project, "/app/git.log")
    if not content:
        return ProjectGitLogResponse(lines=[])
    return ProjectGitLogResponse.from_content(content.decode("utf-8"))


@router.get("/{project_id}/do-deploy/netlify")
async def deploy_netlify(
    team_id: int,
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.query_params.get("token")
    current_user = await get_current_user_from_token(token, db)
    project = await get_project(team_id, project_id, current_user, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    app_name = request.query_params.get("appName")
    if not app_name:
        raise HTTPException(status_code=400, detail="Missing teamSlug or appName")

    async def event_generator():
        sandbox = await DevSandbox.get_or_create(project.id, create_if_missing=False)

        netlify_config = """
[build]
  publish = "frontend/.next"
  command = ""

[[plugins]]
  package = "@netlify/plugin-nextjs"
""".strip()

        await sandbox.run_command(f"echo '{netlify_config}' > /app/netlify.toml")

        yield {
            "event": "message",
            "data": json.dumps({"message": "Installing netlify..."}),
        }
        async for chunk in sandbox.run_command_stream(
            "npm install -g netlify-cli --force"
        ):
            print("netlify-install", repr(chunk))
            pass

        await sandbox.run_command(
            "mkdir -p /app/.config/netlify && mkdir -p /root/.config/netlify"
        )
        await sandbox.run_command(
            "if [ -f /root/.config/netlify/config.json ]; then cp /root/.config/netlify/config.json /app/.config/netlify/config.json; fi"
        )

        yield {
            "event": "message",
            "data": json.dumps({"message": "Logging in to Netlify..."}),
        }
        async for chunk in sandbox.run_command_stream("netlify login"):
            print("netlify-login", repr(chunk))
            url_match = re.search(r"(https://app.netlify.com/[^ ]+)", chunk)
            if url_match:
                url = url_match.group(1)
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"open_url": url, "message": "Login to continue."}
                    ),
                }

        await sandbox.run_command(
            "if [ -f /root/.config/netlify/config.json ]; then cp /root/.config/netlify/config.json /app/.config/netlify/config.json; fi"
        )

        yield {
            "event": "message",
            "data": json.dumps({"message": "Creating site..."}),
        }
        async for chunk in sandbox.run_command_stream(
            f"[ ! -f /app/.netlify/state.json ] && ((sleep 2; echo -n '\n'; sleep 2; echo -n '\n'; sleep 2; echo -n '{app_name}\n') | netlify init)"
        ):
            print("netlify-init", repr(chunk))
            if "already exists" in chunk:
                break

        yield {
            "event": "message",
            "data": json.dumps({"message": "Building site..."}),
        }
        async for chunk in sandbox.run_command_stream(
            "npm run build", workdir="/app/frontend"
        ):
            print("netlify-build", repr(chunk))

        yield {
            "event": "message",
            "data": json.dumps({"message": "Deploying site... ~10 minutes."}),
        }
        opened_url = False
        async for chunk in sandbox.run_command_stream("netlify deploy --prod"):
            print("netlify-deploy", repr(chunk))
            url_match = re.search(r"(https://app.netlify.com/sites[^\s]+)", chunk)
            if url_match and not opened_url:
                url = url_match.group(1)
                yield {
                    "event": "message",
                    "data": json.dumps({"open_url": url}),
                }
                opened_url = True

        print("netlify-complete")

    return EventSourceResponse(event_generator())


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


@router.post("/{project_id}/restart")
async def restart_project(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    from routers.project_socket import project_managers

    if project_id in project_managers:
        await project_managers[project_id].kill()
        del project_managers[project_id]


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
