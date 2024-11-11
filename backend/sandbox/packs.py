from pydantic import BaseModel


class StackPack(BaseModel):
    id: str
    title: str
    description: str
    from_registry: str
    sandbox_start_cmd: str
    stack_description: str


PACKS = [
    StackPack(
        id="vanilla-react",
        title="Vanilla React",
        description="A simple JS React App. Best for starting from scratch with minimal dependencies.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-vanilla-react:latest",
        sandbox_start_cmd="cd /app && if [ ! -d 'frontend' ]; then cp -r /frontend .; fi && cd frontend && npm run dev",
        stack_description="""
You are building a vanilla React app.

The user choose to use a vanilla app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- react-router-dom (use for all routing needs, note this is v6.xx)
- The react app is already created in /app/frontend (do not run `create-react-app`)

Tips:
- Use react-leaflet for maps
- Use https://random.imagecdn.app/<width>/<height> for random images
""".strip(),
    ),
    StackPack(
        id="nextjs-shadcn",
        title="Nextjs Shadcn",
        description="A Nextjs app with Shadcn UI. Best for building a modern web app with a nice UI.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-shadcn:latest",
        sandbox_start_cmd="cd /app && if [ ! -d 'frontend' ]; then cp -r /frontend .; fi && cd frontend && npm start",
        stack_description="""
You are building a Nextjs app with Shadcn UI.

The user choose to use a Nextjs app with Shadcn UI so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Nextjs App Router (use for routing)
- `lucide-react` for icons
- The Nextjs app is already created in /app/frontend (do not run `create-next-app`)

Tips:
- Use react-leaflet for maps
- Use https://random.imagecdn.app/<width>/<height> for random images
""".strip(),
    ),
]

DEFAULT_STACK_PACK_ID = "nextjs-shadcn"


def get_pack_by_id(id: str) -> StackPack:
    return next((pack for pack in PACKS if pack.id == id), None)
