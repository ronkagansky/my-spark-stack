from pydantic import BaseModel


class StackPack(BaseModel):
    title: str
    description: str
    from_registry: str
    sandbox_init_cmd: str
    sandbox_start_cmd: str
    prompt: str


_COPY_FRONTEND_CMD = "if [ ! -d 'frontend' ]; then cp -r /frontend .; fi"
_SETUP_GIT_CMD = "git init && git config --global init.defaultBranch main && git config --global user.email 'bot@prompt-stack.sshh.io' && git config --global user.name 'Prompt Stack Bot' && git add -A && git commit -m 'Initial commit'"
_START_NEXT_JS_CMD = "git config --global user.email 'bot@prompt-stack.sshh.io' && git config --global user.name 'Prompt Stack Bot' && cd /app/frontend && npm run dev"

PACKS = [
    StackPack(
        title="Next.js",
        description="A simple Nextjs App. Best for starting from scratch with minimal components.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-vanilla@sha256:7ef15857dc430f0af0ece838a0fd674dacf1e3bb3975aa2f240e9cdb9ce0297b",
        sandbox_init_cmd=f"cd /app && {_COPY_FRONTEND_CMD} && {_SETUP_GIT_CMD}",
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Next.js app.

The user choose to use a "vanilla" app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- tailwindcss

Style Tips:
- Use inline tailwind classes over custom css
- Use tailwind colors over custom colors
- Assume the user want's a nice look UI out of the box (so add styles as you create components and assume layouts based on what the user is building)

Structure Tips:
- Always use Next.js app router for new pages, creating /src/app/<page>/page.js
- Always ensure new pages are somehow accessible from the main index page
- Always include "use client" unless otherwise specified
- NEVER modify layout.js and use page.js files for layouts

Code Tips:
- NEVER put a <a> in a <Link> tag (Link already uses a <a> tag)

3rd Party Tips:
- Use react-leaflet for maps (you need to install it)
- Use https://random.imagecdn.app/<width>/<height> for placeholder images
""".strip(),
    ),
    StackPack(
        title="Next.js Shadcn",
        description="A Nextjs app with Shadcn UI. Best for building a modern web app with a modern UI.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-shadcn@sha256:77487f76650266c353d485cc11b41e3d5c222c6abddd69942fddcb1d2e108a34",
        sandbox_init_cmd=f"cd /app && {_COPY_FRONTEND_CMD} && {_SETUP_GIT_CMD}",
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Next.js app with Shadcn UI.

The user choose to use a Next.js app with Shadcn UI so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- lucide-react
- axios
- All shadcn components are already installed (import them like `@/components/ui/button`)

Style Tips:
- Use inline tailwind classes over custom css
- Use tailwind colors over custom colors
- Prefer shadcn components as much as possible over custom components
- Assume the user want's a nice look UI out of the box (so add styles as you create components and assume layouts based on what the user is building)

Structure Tips:
- Always use Next.js app router for new pages, creating /src/app/<page>/page.js
- Always ensure new pages are somehow accessible from the main index page
- Always include "use client" unless otherwise specified
- NEVER modify layout.js and use page.js files for layouts

Code Tips:
- NEVER put a <a> in a <Link> tag (Link already uses a <a> tag)

3rd Party Tips:
- Use react-leaflet for maps (you need to install it)
- Use https://random.imagecdn.app/<width>/<height> for placeholder images
""".strip(),
    ),
]
