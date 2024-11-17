from pydantic import BaseModel


class StackPack(BaseModel):
    title: str
    description: str
    from_registry: str
    sandbox_init_cmd: str
    sandbox_start_cmd: str
    prompt: str


_COPY_FRONTEND_CMD = "if [ ! -d 'frontend' ]; then cp -r /frontend .; fi"
_SETUP_GIT_CMD = "git init && git config --global user.email 'bot@prompt-stack.sshh.io' && git config --global user.name 'Prompt Stack Bot' && git add -A && git commit -m 'Initial commit'"

PACKS = [
    StackPack(
        title="Vanilla Nextjs",
        description="A simple Nextjs App. Best for starting from scratch with minimal components.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-vanilla-nextjs@sha256:8e4377feb2f989f7bea506aacb477936ae08aa95c68d5fb5fe8cec2395fa4342",
        sandbox_init_cmd=f"cd /app && {_COPY_FRONTEND_CMD} && {_SETUP_GIT_CMD}",
        sandbox_start_cmd="cd /app/frontend && npm run dev",
        prompt="""
You are building a Nextjs app.

The user choose to use a "vanilla" app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- react-router-dom (use for all routing needs, note this is v6.xx)
- The react app is already created in /app/frontend (do not run `create-react-app`)

Tips:
- Put initial app changes in App.js and move to other files only as things get more complex
- Use react-leaflet for maps
- Use inline styles over custom css
- Use https://random.imagecdn.app/<width>/<height> for random images
- Always link new pages in App.js (or else the user will not see them)
""".strip(),
    ),
    StackPack(
        title="Nextjs Shadcn",
        description="A Nextjs app with Shadcn UI. Best for building a modern web app with a modern UI.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-shadcn@sha256:1e4d19582567f98b4672d346472867dcb475e32bdb8e2c43a9ee6b0bdf4a57c5",
        sandbox_init_cmd=f"cd /app && {_COPY_FRONTEND_CMD} && {_SETUP_GIT_CMD}",
        sandbox_start_cmd="cd /app/frontend && npm run dev",
        prompt="""
You are building a Nextjs app with Shadcn UI.

The user choose to use a Nextjs app with Shadcn UI so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Nextjs App Router (use for routing)
- `lucide-react` for icons
- Most shadcn components are already installed with `npx shadcn@latest add --yes --all` (import them like `@/components/ui/button`)
- The Nextjs app is already created in /app/frontend (do not run `create-next-app`)

Tips:
- Put initial app changes in src/app/page.js and move to other files only as things get more complex
- Use react-leaflet for maps
- Always include "use client" unless otherwise specified
- Always use tailwind classes over custom css
- Always link new pages in App.js (or else the user will not see them)
- Always use app router for new pages, creating /src/app/<page>/page.js
- Always use shadcn components over custom components
""".strip(),
    ),
]
