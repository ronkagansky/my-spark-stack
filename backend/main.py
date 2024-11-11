from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db, get_db
from db.models import Project
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from sqlalchemy import select

from routers import auth, projects, websockets, stacks


async def periodic_task():
    db = next(get_db())
    while True:
        print("Running periodic task...")
        # Find projects with sandboxes inactive for 10+ minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)
        query = select(Project).where(
            Project.modal_active_sandbox_last_used_at <= cutoff_time
        )
        inactive_projects = db.execute(query).scalars().all()

        for project in inactive_projects:
            print(f"Found inactive sandbox for project {project.id}")
            # You can add additional handling here if needed

        await asyncio.sleep(60)


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
app.include_router(websockets.router)
app.include_router(stacks.router)

if __name__ == "__main__":
    init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
