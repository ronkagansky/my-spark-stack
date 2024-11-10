from pydantic import BaseModel


class StackPack(BaseModel):
    id: str
    title: str
    description: str
    from_registry: str
    sandbox_start_cmd: str


PACKS = [
    StackPack(
        id="vanilla-react",
        title="Vanilla React",
        description="A simple JS React App. Best for starting from scratch with minimal dependencies.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-vanilla-react:latest",
        sandbox_start_cmd="cd /app && if [ ! -d 'frontend' ]; then cp -r /frontend .; fi && cd frontend && npm start",
    )
]
