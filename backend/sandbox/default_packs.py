from pydantic import BaseModel, computed_field
import hashlib


class StackPack(BaseModel):
    title: str
    description: str
    from_registry: str
    sandbox_init_cmd: str
    sandbox_start_cmd: str
    prompt: str
    setup_time_seconds: int

    @computed_field
    def pack_hash(self) -> str:
        """Generate a unique hash for this pack based on init command and registry."""
        content = f"{self.sandbox_init_cmd}{self.from_registry}".encode()
        return hashlib.sha256(content).hexdigest()[:12]


_SETUP_NEXT_JS_CMD = """
cd /app

if [ ! -d 'frontend' ]; then 
    cp -r /frontend .; 
fi

git config --global user.email 'bot@prompt-stack.sshh.io'
git config --global user.name 'Prompt Stack Bot'
if [ ! -d ".git" ]; then
    git init
    git config --global init.defaultBranch main
    git add -A
    git commit -m 'Initial commit'
fi

cat > .gitignore << 'EOF'
node_modules/
.config/
.env
.next/
.cache/
.netlify/
*.log
dist/
build/
EOF

if [ ! -f '/app/.env' ]; then
    touch /app/.env
fi
set -a
[ -f /app/.env ] && . /app/.env
set +a

curl -o /app/frontend/next.config.mjs https://raw.githubusercontent.com/sshh12/prompt-stack/refs/heads/main/images/next.config.mjs.example
""".strip()

_START_NEXT_JS_CMD = f"""
{_SETUP_NEXT_JS_CMD}
cd /app/frontend
npm run dev
""".strip()

PACKS = [
    StackPack(
        title="Next.js",
        description="A simple Nextjs App. Best for starting from scratch with minimal components.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-vanilla@sha256:7ef15857dc430f0af0ece838a0fd674dacf1e3bb3975aa2f240e9cdb9ce0297b",
        sandbox_init_cmd=_SETUP_NEXT_JS_CMD,
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Next.js app.

The user choose to use a "vanilla" app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- tailwindcss
- `npm install` already run for these

Style Tips:
- Use inline tailwind classes over custom css
- Use tailwind colors over custom colors
- Assume the user want's a nice look UI out of the box (so add styles as you create components and assume layouts based on what the user is building)
- Remove Next.js boilerplate text from the index page

Structure Tips:
- Always use Next.js app router for new pages, creating /src/app/<page>/page.js
- Always ensure new pages are somehow accessible from the main index page
- Always include "use client" unless otherwise specified
- NEVER modify layout.js and use page.js files for layouts

Code Tips:
- NEVER put a <a> in a <Link> tag (Link already uses a <a> tag)

3rd Party Tips:
- If you need to build a map, use react-leaflet
    1. $ npm install react-leaflet leaflet
    2. `import { MapContainer, TileLayer, useMap } from 'react-leaflet'` (you do not need css imports)
- If you need placeholder images, use https://prompt-stack.sshh.io/api/mocks/images[?orientation=landscape&query=topic] (this will redirect to a rand image)
""".strip(),
        setup_time_seconds=60,
    ),
    StackPack(
        title="Next.js Shadcn",
        description="A Nextjs app with Shadcn UI. Best for building a modern web app with a modern UI.",
        from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-shadcn@sha256:8e6a2e6752f8f4884ed03925db0514aea4678825890cb106bbcd598d91fe0e8b",
        sandbox_init_cmd=_SETUP_NEXT_JS_CMD,
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Next.js app with Shadcn UI.

The user choose to use a Next.js app with Shadcn UI so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- lucide-react v0.460
- axios v1.7
- recharts v2.13
- All shadcn components are already installed (import them like `@/components/ui/button`)
- `npm install` already run for these

Style Tips:
- Use inline tailwind classes over custom css
- Use tailwind colors over custom colors
- Prefer shadcn components as much as possible over custom components
- Assume the user want's a nice look UI out of the box (so add styles as you create components and assume layouts based on what the user is building)
- Remove Next.js boilerplate text from the index page

Structure Tips:
- Always use Next.js app router for new pages, creating /src/app/<page>/page.js
- Always ensure new pages are somehow accessible from the main index page
- Always include "use client" unless otherwise specified
- NEVER modify layout.js and use page.js files for layouts

Code Tips:
- NEVER put a <a> in a <Link> tag (Link already uses a <a> tag)

3rd Party Tips:
- If you need to build a map, use react-leaflet
    1. $ npm install react-leaflet leaflet
    2. `import { MapContainer, TileLayer, useMap } from 'react-leaflet'` (you do not need css imports)
- If you need placeholder images, use https://prompt-stack.sshh.io/api/mocks/images[?orientation=landscape&query=topic] (this will redirect to a rand image)
""".strip(),
        setup_time_seconds=60,
    ),
]
