from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db, get_db
from contextlib import asynccontextmanager
import asyncio

from sandbox.sandbox import maintain_prepared_sandboxes, clean_up_project_resources
from routers import project_socket, auth, projects, stacks, teams, chats, uploads
from config import RUN_PERIODIC_CLEANUP


async def periodic_task():
    if not RUN_PERIODIC_CLEANUP:
        return
    db = next(get_db())
    while True:
        exceptions = await asyncio.gather(
            maintain_prepared_sandboxes(db),
            clean_up_project_resources(db),
            return_exceptions=True,
        )
        for e in exceptions:
            if isinstance(e, Exception):
                print("Error maintaining sandboxes", e)
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
