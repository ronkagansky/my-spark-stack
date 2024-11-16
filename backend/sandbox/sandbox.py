import modal
import aiohttp
import asyncio
import base64
import datetime
import uuid
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from modal.volume import FileEntryType

from db.database import get_db
from db.models import Project, PreparedSandbox, Stack

TARGET_SANDBOXES_PER_STACK = 1

app = modal.App.lookup("prompt-stack-sandbox", create_if_missing=True)


IGNORE_PATHS = ["node_modules", ".git", ".next", "build"]


def _unique_id():
    return str(uuid.uuid4())


async def _wait_for_up(url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status < 500
    except:
        return False


async def _vol_to_paths(vol: modal.Volume):
    paths = []
    entries = await vol.listdir.aio("/", recursive=False)

    def _ends_with_ignore_path(path: str):
        path_parts = path.split("/")
        return any(
            part == ignore_path for ignore_path in IGNORE_PATHS for part in path_parts
        )

    async def _recurse(path: str):
        entries = await vol.listdir.aio(path, recursive=False)
        for entry in entries:
            if _ends_with_ignore_path(entry.path):
                continue
            if entry.type == FileEntryType.DIRECTORY:
                await _recurse(entry.path)
            else:
                paths.append(entry.path)

    for entry in entries:
        if _ends_with_ignore_path(entry.path):
            continue
        if entry.type == FileEntryType.DIRECTORY:
            await _recurse(entry.path)
        else:
            paths.append(entry.path)

    return paths


class DevSandbox:
    def __init__(self, project_id: int, sb: modal.Sandbox, vol: modal.Volume):
        self.project_id = project_id
        self.sb = sb
        self.vol = vol
        self.ready = False

    async def wait_for_up(self):
        while True:
            tunnels = await self.sb.tunnels.aio()
            tunnel_url = tunnels[3000].url
            if await _wait_for_up(tunnel_url):
                break

            await asyncio.sleep(3)
        self.ready = True

    async def get_file_paths(self) -> List[str]:
        paths = await _vol_to_paths(self.vol)
        return sorted(["/app/" + path for path in paths])

    async def run_command(self, command: str, workdir: Optional[str] = None) -> str:
        try:
            proc = await self.sb.exec.aio(
                "sh", "-c", command, workdir=workdir or "/app"
            )
            await proc.wait.aio()
            return (await proc.stdout.read.aio()) + (await proc.stderr.read.aio())
        except Exception as e:
            return f"Error: {e}"

    async def write_file_contents(self, files: List[Tuple[str, str]]):
        # Create a single Python command that writes all files at once
        files_data = []
        for path, content in files:
            encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            files_data.append((path, encoded_content))

        python_cmd = """
import os
import base64

files = %s

for path, base64_content in files:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(base64.b64decode(base64_content).decode('utf-8'))
""" % str(
            files_data
        )

        proc = await self.sb.exec.aio(
            "python3",
            "-c",
            python_cmd,
            workdir="/app",
        )
        await proc.wait.aio()

    async def read_file_contents(self, path: str) -> str:
        if path.startswith("/app/"):
            path = path[len("/app/") :]
        content = []
        async for chunk in self.vol.read_file.aio(path):
            content.append(chunk.decode("utf-8"))
        return "".join(content)

    @classmethod
    async def delete(cls, project_id: int):
        try:
            async for sb in modal.Sandbox.list.aio(
                tags={"project_id": str(project_id)}
            ):
                await sb.terminate.aio()
        except:
            pass
        try:
            await modal.Volume.delete.aio(f"prompt-stack-vol-project-{project_id}")
        except:
            pass

    @classmethod
    async def get_or_create(cls, project_id: int) -> "DevSandbox":
        db = next(get_db())
        project = db.query(Project).filter(Project.id == project_id).first()
        stack = db.query(Stack).filter(Stack.id == project.stack_id).first()

        if not project.modal_volume_label:
            existing_psb = (
                db.query(PreparedSandbox)
                .filter(PreparedSandbox.stack_id == stack.id)
                .first()
            )
            if not existing_psb:
                raise Exception(
                    f"No prepared sandbox found for stack {stack.id} (project {project_id})"
                )

            project.modal_volume_label = existing_psb.modal_volume_label
            db.delete(existing_psb)
            db.commit()
            print(
                f"Using existing prepared sandbox for project {existing_psb.id} -> {project_id}"
            )

        vol = modal.Volume.from_name(project.modal_volume_label)

        if project.modal_sandbox_id:
            sb = await modal.Sandbox.from_id.aio(project.modal_sandbox_id)
            poll_code = await sb.poll.aio()
            return_code = sb.returncode
            sb_is_up = ((poll_code is None) or (return_code is None)) or (
                poll_code == 0 and return_code == 0
            )
        else:
            sb_is_up = False
        if not sb_is_up:
            print(
                "Creating sandbox for project",
                project.id,
                project.modal_sandbox_id,
            )

            image = modal.Image.from_registry(stack.from_registry, add_python=None)
            sb = await modal.Sandbox.create.aio(
                "sh",
                "-c",
                stack.sandbox_start_cmd,
                app=app,
                volumes={"/app": vol},
                image=image,
                encrypted_ports=[3000],
                timeout=3 * 60 * 60,
                cpu=1,
                memory=1024,
            )
            project.modal_sandbox_id = sb.object_id
            project.modal_sandbox_last_used_at = datetime.datetime.now()
            db.commit()
            await sb.set_tags.aio({"project_id": str(project_id)})
        else:
            print("Using existing sandbox for project", project.id)
            sb = await modal.Sandbox.from_id.aio(project.modal_sandbox_id)

        return cls(project_id, sb, vol)


async def maintain_prepared_sandboxes(db: Session):
    stacks = db.query(Stack).all()
    for stack in stacks:
        psboxes = (
            db.query(PreparedSandbox).filter(PreparedSandbox.stack_id == stack.id).all()
        )
        psboxes_to_add = max(0, TARGET_SANDBOXES_PER_STACK - len(psboxes))
        if psboxes_to_add == 0:
            continue
        print(
            f"Creating {psboxes_to_add} prepared sandboxes for stack {stack.title} ({stack.id})"
        )
        for _ in range(psboxes_to_add):
            vol_id = f"prompt-stack-vol-{_unique_id()}"
            vol = modal.Volume.from_name(vol_id, create_if_missing=True)
            image = modal.Image.from_registry(stack.from_registry, add_python=None)
            sb = await modal.Sandbox.create.aio(
                "sh",
                "-c",
                stack.sandbox_init_cmd,
                app=app,
                volumes={"/app": vol},
                image=image,
                timeout=5 * 60,
                cpu=1,
                memory=512,
            )
            await sb.wait.aio()
            psb = PreparedSandbox(
                stack_id=stack.id,
                modal_sandbox_id=sb.object_id,
                modal_volume_label=vol_id,
            )
            db.add(psb)
            db.commit()
