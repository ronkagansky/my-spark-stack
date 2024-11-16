from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db, get_db
from db.models import Project
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import asyncio
import modal

from sandbox.sandbox import maintain_prepared_sandboxes
from routers import project_socket, auth, projects, stacks, teams, chats, uploads


async def periodic_task():
    db = next(get_db())
    while True:
        try:
            await maintain_prepared_sandboxes(db)
        except Exception as e:
            print("Error maintaining prepared sandboxes", e)
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
app.include_router(project_socket.router)
app.include_router(stacks.router)
app.include_router(teams.router)
app.include_router(chats.router)
app.include_router(uploads.router)

if __name__ == "__main__":
    init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
