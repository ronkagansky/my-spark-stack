import traceback
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import functools
import modal

from routers.project_socket import project_managers
from db.models import Project, PreparedSandbox, Stack
from sandbox.sandbox import DevSandbox
from config import TARGET_PREPARED_SANDBOXES_PER_STACK, PROJECT_RESOURCE_TIMEOUT_SECONDS

def task_handler():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                print(f"Error in {func.__name__}: {e}\n{traceback.format_exc()}")
                return None
        return wrapper
    return decorator

@task_handler()
async def cleanup_inactive_project_managers():
    try:
        to_remove = []
        for project_id, manager in project_managers.items():
            if manager.is_inactive():
                to_remove.append(project_id)

        for project_id in to_remove:
            await project_managers[project_id].kill()
            del project_managers[project_id]
            print(f"Cleaned up inactive project manager for project {project_id}")
    except Exception as e:
        print(f"Error in cleanup_inactive_project_managers: {e}\n{traceback.format_exc()}")

@task_handler()
async def maintain_prepared_sandboxes(db: Session):
    try:
        stacks = db.query(Stack).all()
        for stack in stacks:
            psboxes = db.query(PreparedSandbox).filter(
                PreparedSandbox.stack_id == stack.id
            ).all()
            psboxes_to_add = max(0, TARGET_PREPARED_SANDBOXES_PER_STACK - len(psboxes))

            if psboxes_to_add > 0:
                print(
                    f"Creating {psboxes_to_add} prepared sandboxes for stack {stack.title} ({stack.id})"
                )
                for _ in range(psboxes_to_add):
                    try:
                        sb, vol_id = await DevSandbox.prepare_sandbox(stack)
                        psbox = PreparedSandbox(
                            stack_id=stack.id,
                            modal_sandbox_id=sb.object_id,
                            modal_volume_label=vol_id,
                            pack_hash=stack.pack_hash,
                        )
                        db.add(psbox)
                        db.commit()
                    except Exception as sandbox_err:
                        db.rollback()
                        print(f"Failed to prepare sandbox for stack {stack.id}: {sandbox_err}")

        latest_stack_hashes = {stack.pack_hash for stack in stacks}
        psboxes_to_delete = db.query(PreparedSandbox).filter(
            (PreparedSandbox.pack_hash.notin_(latest_stack_hashes))
            | (PreparedSandbox.pack_hash.is_(None))
        ).all()
        if psboxes_to_delete:
            print(f"Deleting {len(psboxes_to_delete)} prepared sandboxes with stale hashes")
            for psbox in psboxes_to_delete:
                try:
                    db.delete(psbox)
                    db.commit()
                    await modal.Volume.delete.aio(name=psbox.modal_volume_label)
                except Exception as delete_err:
                    db.rollback()
                    print(f"Failed to delete prepared sandbox {psbox.id}: {delete_err}")
    except Exception as e:
        db.rollback()
        print(f"Error in maintain_prepared_sandboxes: {e}\n{traceback.format_exc()}")

@task_handler()
async def clean_up_project_resources(db: Session = None):
    try:
        projects = db.query(Project).filter(
            Project.modal_sandbox_id.isnot(None),
            Project.modal_sandbox_last_used_at.isnot(None),
            Project.modal_sandbox_last_used_at < datetime.now() - timedelta(
                seconds=PROJECT_RESOURCE_TIMEOUT_SECONDS
            ),
            (Project.modal_never_cleanup.is_(None) | ~Project.modal_never_cleanup),
        ).all()

        if projects:
            print(f"Cleaning up projects {[p.id for p in projects]}")
            for project in projects:
                try:
                    await DevSandbox.terminate_project_resources(project)
                    project.modal_sandbox_id = None
                    project.modal_sandbox_expires_at = None
                    db.commit()
                except Exception as proj_err:
                    db.rollback()
                    print(f"Failed cleaning resources for project {project.id}: {proj_err}")
    except Exception as e:
        db.rollback()
        print(f"Error in clean_up_project_resources: {e}\n{traceback.format_exc()}")
