from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import and_
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import StreamingResponse, JSONResponse
import json
import re
import io

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
from sandbox.sandbox import DevSandbox, SandboxNotReadyException
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


@router.post("/{project_id}/zip")
async def generate_project_zip(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        sandbox = await DevSandbox.get_or_create(project.id, create_if_missing=False)
    except SandboxNotReadyException:
        raise HTTPException(status_code=400, detail="Sandbox not ready. Project must be running.")

    git_sha = await sandbox.run_command("git rev-parse HEAD")
    if not git_sha.strip():
        git_sha = "init"
    else:
        git_sha = git_sha.strip()[:10]
    git_sha_fn = f"app-{project.id}-{git_sha}.zip".replace(" ", "-")

    # I dont know why but getting it to ignore has been a pain
    exclude_content = """
**/node_modules/**
**/.next/**
**/build/**
git.log
**/git.log
tmp
tmp/
**/tmp
**/tmp/
/tmp
/tmp/
.git
.git/
**/.git
**/.git/
""".strip()
    await sandbox.run_command(f"echo '{exclude_content}' > /tmp/zip-exclude.txt")
    await sandbox.run_command("mkdir -p /app/tmp")
    
    # Clean up any tmp directories before zipping
    await sandbox.run_command("find /app -type d -name 'tmp' -exec rm -rf {} +")
    
    out = await sandbox.run_command(
        f"cd /app && zip -r /app/tmp/{git_sha_fn} . -x@/tmp/zip-exclude.txt"
    )

    return JSONResponse(content={"url": f"/api/teams/{team_id}/projects/{project_id}/download-zip?path={git_sha_fn}"})


@router.get("/{project_id}/download-zip")
async def get_project_download_zip(
    team_id: int,
    project_id: int,
    path: str = Query(..., description="Path to the zip file"),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate path format and prevent directory traversal
    expected_prefix = f"app-{project_id}-"
    if (
        not path.startswith(expected_prefix) 
        or not path.endswith(".zip")
        or "/" in path 
        or "\\" in path 
        or ".." in path
        or not re.match(r"^app-\d+-[a-f0-9]{1,10}\.zip$", path)
    ):
        raise HTTPException(status_code=400, detail="Invalid zip file path")

    try:
        sandbox = await DevSandbox.get_or_create(project.id, create_if_missing=False)
        file_size = await sandbox.run_command(f"stat -c%s /app/tmp/{path}")
        file_size = int(file_size.strip())

        async def _stream_zip():
            try:
                async for chunk in sandbox.stream_file_contents(f"/app/tmp/{path}", binary_mode=True):
                    yield chunk
            finally:
                # Clean up the zip file after streaming
                await sandbox.run_command(f"rm -f /tmp/{path}")

        return StreamingResponse(
            _stream_zip(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{path}"',
                "Content-Length": str(file_size)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error accessing zip file: {str(e)}")