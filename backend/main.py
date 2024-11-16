from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db, get_db
from db.models import Project
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import asyncio
import modal

from routers import project_socket, auth, projects, stacks, teams, chats


async def periodic_task():
    pass
    # await asyncio.sleep(10)
    # db = next(get_db())
    # while True:
    #     print("Running periodic task...")
    #     # Find projects with sandboxes inactive for 10+ minutes
    #     try:
    #         cutoff_time = datetime.now() - timedelta(minutes=10)
    #         inactive_projects = (
    #             db.query(Project)
    #             .filter(
    #                 (Project.modal_active_sandbox_last_used_at <= cutoff_time)
    #                 & (Project.modal_active_sandbox_id.is_not(None))
    #             )
    #             .all()
    #         )

    #         for project in inactive_projects:
    #             print(
    #                 f"Found inactive sandbox for project={project.id}"
    #                 f" and sandbox_id={project.modal_active_sandbox_id} (last used at {project.modal_active_sandbox_last_used_at})"
    #             )
    #             sb = await modal.Sandbox.from_id.aio(project.modal_active_sandbox_id)
    #             await sb.terminate.aio()
    #             project.modal_active_sandbox_id = None
    #             project.modal_active_sandbox_last_used_at = None
    #             db.commit()
    #     except Exception as e:
    #         print(f"periodic_task() error: {e}")

    #     await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(periodic_task())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://*.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(project_socket.router)
app.include_router(stacks.router)
app.include_router(teams.router)
app.include_router(chats.router)

if __name__ == "__main__":
    init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
