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


_SETUP_COMMON_CMD = """
cd /app

if [ ! -d 'frontend' ]; then 
    cp -r /frontend .; 
fi

if [ -f /app/frontend/package.json ]; then
    cat /app/frontend/package.json
    ls -l /app/frontend
fi

git config --global user.email 'bot@sparkstack.app'
git config --global user.name 'Spark Stack Bot'
git config --global init.defaultBranch main
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
tmp/
EOF

if [ ! -f '/app/.env' ]; then
    touch /app/.env
fi
if ! grep -q "^IS_SPARK_STACK=" /app/.env; then
    echo "IS_SPARK_STACK=true\n" >> /app/.env
fi
set -a
[ -f /app/.env ] && . /app/.env
set +a
""".strip()

_START_NEXT_JS_CMD = f"""
{_SETUP_COMMON_CMD}
cd /app/frontend
npm run dev
""".strip()

_START_ANGULAR_CMD = f"""
{_SETUP_COMMON_CMD}
cd /app/frontend
npm run start -- --host 0.0.0.0 --port 3000
""".strip()


PACKS = [
    StackPack(
        title="Next.js",
        description="A simple Next.js app. Best for starting from scratch with minimal components.",
        from_registry="ghcr.io/sshh12/spark-stack-pack-nextjs-vanilla:latest",
        sandbox_init_cmd=_SETUP_COMMON_CMD,
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Next.js app.

The user chose to use a "vanilla" app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- tailwindcss
- `npm install` done
- /app/.env, /app/.git

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
        description="A Next.js app with Shadcn and Supabase. Best for building a modern web app with a clean UI.",
        from_registry="ghcr.io/sshh12/spark-stack-pack-nextjs-shadcn:781248fc6c7745dc2657679a79e9226f3f680fd89388564883d33c39f1a4ff32",
        sandbox_init_cmd=_SETUP_COMMON_CMD,
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Next.js app with Shadcn and Supabase.

The user chose to use a Next.js app with Shadcn and Supabase so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- lucide-react v0.460
- axios v1.7
- recharts v2.13
- Supabase v1.13
- All shadcn components (import them like `@/components/ui/button`)
- `npm install` done
- /app/.env, /app/.git

Style Tips:
- Use inline tailwind classes over custom css
- Use tailwind colors over custom colors
- Prefer shadcn components as much as possible over custom components
- Assume the user wants a nice looking UI out of the box (so add styles as you create components and assume layouts based on what the user is building)
- Remove Next.js boilerplate text from the index page

Structure Tips:
- Always use Next.js app router for new pages, creating /src/app/<page>/page.js
- Always ensure new pages are somehow accessible from the main index page
- Prefer "use client" unless otherwise specified
- NEVER modify layout.js and use page.js files for layouts

Code Tips:
- NEVER put a <a> in a <Link> tag (Link already uses a <a> tag)

3rd Party Tips:
- If you need to build a map, use react-leaflet
    1. $ npm install react-leaflet leaflet
    2. `import { MapContainer, TileLayer, useMap } from 'react-leaflet'` (you do not need css imports)
- If you need placeholder images, use https://sparkstack.app/api/mocks/images[?orientation=landscape&query=topic] (this will redirect to a rand image)
""".strip(),
        setup_time_seconds=60,
    ),
    StackPack(
        title="p5.js",
        description="A simple app with p5.js. Best for generative art, games, and simulations.",
        from_registry="ghcr.io/sshh12/spark-stack-pack-nextjs-p5:latest",
        sandbox_init_cmd=_SETUP_COMMON_CMD,
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a p5.js sketch within a Next.js app.

The user ONLY wants to build a p5.js sketch, do not attempt to use any Next.js features or other React features.

Already included:
- Next.js v15 (app already created)
- p5.js v1.11.2
- Addons: p5.sound.min.js, p5.collide2d
- /app/.env, /app/.git

Style Tips:
- Keep your code clean and readable
- Use p5.js best practices

Structure Tips:
- ALL changes and features should be in /app/frontend/public/{sketch,helpers,objects}.js
- Organize "objects" (balls, items, etc) into objects.js
- Organize "utils" (utility functions, etc) into helpers.js
- At all times, sketch.js should include setup() windowResized() and draw() functions
- If the user wants to add a p5.js addon, edit layout.js to add a new <Script> (following existing scripts in that files)

```javascript
// /app/frontend/public/sketch.js
// example sketch.js
... variables ...

function setup() {
  createCanvas(windowWidth, windowHeight);
  ...
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

function draw() {
  background(0);
  ...
}
```

```javascript
// /app/frontend/public/objects.js
// example objects.js

class Ball {
  constructor(x, y, size = 30) {
    // ... init code ...
  }

  update() {
    // ... update code ...
  }

  draw() {
    // ... draw code ...
  }
} 
```
""".strip(),
        setup_time_seconds=60,
    ),
    StackPack(
        title="Pixi.js",
        description="A app with Pixi.js. Best for games and animations.",
        from_registry="ghcr.io/sshh12/spark-stack-pack-nextjs-pixi:latest",
        sandbox_init_cmd=_SETUP_COMMON_CMD,
        sandbox_start_cmd=_START_NEXT_JS_CMD,
        prompt="""
You are building a Pixi.js app within a Next.js app.

The user ONLY wants to build a Pixi.js app, do not attempt to use any Next.js features or other React features.

Already included:
- Next.js v15 (app already created)
- Pixi.js v8.6.6
- Addons: @pixi/mesh-extras
- /app/.env, /app/.git

Style Tips:
- Keep your code clean and readable
- Use Pixi.js best practices

Structure Tips:
- ALL changes and features should be in /app/frontend/app/src/pixi/*.js
- At all times, /app/frontend/app/src/pixi/app.js should include "new Application()" and "await app.init(...)"

```javascript
// /app/frontend/app/src/pixi/app.js
// example app.js
import { Application, Assets, Graphics, MeshRope, Point } from 'pixi.js';

(async () =>
{
    const app = new Application();
    await app.init({ resizeTo: window });
    document.body.appendChild(app.canvas);

    // ... pixi code ...
})();
```
""".strip(),
        setup_time_seconds=60,
    ),
    StackPack(
        title="Angular",
        description="A simple Angular app. Best for starting from scratch with Angular and minimal components.",
        from_registry="ghcr.io/sshh12/spark-stack-pack-angular-vanilla:latest",
        sandbox_init_cmd=_SETUP_COMMON_CMD,
        sandbox_start_cmd=_START_ANGULAR_CMD,
        prompt="""
You are building an Angular app.

The user chose to use a "vanilla" app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Angular v19 (app already created)
- `npm install` done
- /app/.env, /app/.git

Style Tips:
- Assume the user wants a nice looking UI out of the box (so add styles as you create components and assume layouts based on what the user is building)
- At the start, remove Angular boilerplate text from the index page

Structure Tips:
- Always use Angular's CLI to generate new components, services, etc.
- Always ensure new components and pages are somehow accessible from the main app component
- NEVER modify main.ts and use app.component.ts files for layouts

Code Tips:
- NEVER put a <a> in a <routerLink> tag (routerLink already uses a <a> tag)

3rd Party Tips:
- If you need to build a map, use @angular/google-maps
    1. $ npm install @angular/google-maps
    2. `import { GoogleMapsModule } from '@angular/google-maps'` (you do not need css imports)
- If you need placeholder images, use https://prompt-stack.sshh.io/api/mocks/images[?orientation=landscape&query=topic] (this will redirect to a random image)
""".strip(),
        setup_time_seconds=60,
    ),
]
