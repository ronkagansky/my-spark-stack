from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import and_
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import StreamingResponse, JSONResponse
import requests
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
    
@router.get("/{project_id}/deploy-status/github")
async def deploy_status_github(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    sandbox = await DevSandbox.get_or_create(project.id, create_if_missing=False)
    has_origin = "origin" in await sandbox.run_command("git remote -v")
    env_text = await sandbox.run_command("cat /app/.env")
    has_token = "GITHUB_TOKEN" in env_text

    try:
        repo_name = re.search(r"GITHUB_REPO=(.*)", env_text).group(1)
    except Exception:
        repo_name = None

    return JSONResponse(content={"created": has_token and has_origin, "repo_name": repo_name})

@router.post("/{project_id}/deploy-push/github")
async def deploy_push_github(
    team_id: int,
    project_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    project = get_project_for_user(db, team_id, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    sandbox = await DevSandbox.get_or_create(project.id, create_if_missing=False)

    out = await sandbox.run_command("git push -u origin main --force")
    print(out)

    return JSONResponse(content={"done": True})


@router.get("/{project_id}/deploy-create/github")
async def deploy_create_github(
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

    github_token = request.query_params.get("githubToken")
    if not github_token:
        raise HTTPException(status_code=400, detail="Missing githubToken")
    
    repo_name = project.name.replace(" ", "-").lower()

    async def event_generator():

        sandbox = await DevSandbox.get_or_create(project.id, create_if_missing=False)

        yield {
            "event": "message",
            "data": json.dumps({"message": "Creating repository..."}),
        }

        remotes = await sandbox.run_command("git remote -v")
        if 'origin' not in remotes:

            create_repo_data= requests.post("https://api.github.com/user/repos", headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }, json={
                "name": repo_name,
            }).json()

            yield {
                "event": "message",
                "data": json.dumps({"message": "Connecting to repository..."}),
            }

            if 'already exists' in repr(create_repo_data):
                owner_name = requests.get("https://api.github.com/user", headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }).json()["login"]
                full_name = f"{owner_name}/{repo_name}"
            else:
                full_name = create_repo_data["full_name"]
                owner_name = create_repo_data["owner"]["login"]

            await sandbox.run_command(f"git remote add origin https://{owner_name}:{github_token}@github.com/{full_name}.git")
            yield {
                "event": "message",
                "data": json.dumps({"message": "Pushing to repository..."}),
            }
            await sandbox.run_command("git branch -M main")
            await sandbox.run_command("git push -u origin main")
            await sandbox.run_command(f"echo -n 'GITHUB_TOKEN={github_token}\nGITHUB_REPO={full_name}\nGITHUB_OWNER={owner_name}\n' >> /app/.env")

        yield {
            "event": "message",
            "data": json.dumps({"done": True}),
        }

    return EventSourceResponse(event_generator())
