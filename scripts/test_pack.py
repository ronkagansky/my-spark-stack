"""
python ../scripts/test_pack.py
"""

import sys

sys.path.append("../")
sys.path.append("../backend")

import asyncio
import modal
import uuid
from backend.sandbox.default_packs import (
    StackPack,
    _SETUP_COMMON_CMD,
    _START_NEXT_JS_CMD,
)
from backend.sandbox.sandbox import app

# Define your test pack here
TEST_PACK = StackPack(
    title="Next.js",
    description="A simple Nextjs App. Best for starting from scratch with minimal components.",
    from_registry="ghcr.io/sshh12/prompt-stack-pack-nextjs-vanilla@sha256:293b552ccb5a72ec6d0f87fa85b7be17c68469991d9fcb4989dce98527bee95d",
    sandbox_init_cmd=_SETUP_COMMON_CMD,
    sandbox_start_cmd=_START_NEXT_JS_CMD,
    prompt="""
You are building a Next.js app.

The user chose to use a "vanilla" app so avoid adding any additional dependencies unless they are explicitly asked for.

Already included:
- Next.js v15 (app already created)
- tailwindcss
- `npm install` already run for these
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
)


async def main():
    vol_id = None
    sb = None
    try:
        print("Creating sandbox for test pack...")

        # Create volume
        vol_id = f"prompt-stack-vol-{str(uuid.uuid4())}"
        vol = modal.Volume.from_name(vol_id, create_if_missing=True)
        print(f"Created volume: {vol_id}")

        # Create init sandbox
        image = modal.Image.from_registry(TEST_PACK.from_registry, add_python=None)
        init_sb = await modal.Sandbox.create.aio(
            "sh",
            "-c",
            TEST_PACK.sandbox_init_cmd,
            app=app,
            volumes={"/app": vol},
            image=image,
            timeout=5 * 60,
            cpu=0.125,
            memory=256,
        )
        print(f"Running init sandbox (id={init_sb.object_id})")
        await init_sb.wait.aio()

        # Create start sandbox
        sb = await modal.Sandbox.create.aio(
            "sh",
            "-c",
            TEST_PACK.sandbox_start_cmd,
            app=app,
            volumes={"/app": vol},
            image=image,
            encrypted_ports=[3000],
            timeout=60 * 60,
            cpu=0.125,
            memory=1024 * 2,
        )
        print(f"Created start sandbox (id={sb.object_id})")

        print("Waiting for sandbox to be ready...")
        await asyncio.sleep(5)  # Give it a moment to start

        tunnels = await sb.tunnels.aio()
        tunnel_url = tunnels[3000].url
        print(f"\nSandbox is ready!")
        print(f"Tunnel URL: {tunnel_url}")

        print("\nPress Ctrl+C to terminate the sandbox")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nTerminating sandbox...")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        if sb:
            await sb.terminate.aio()
        if vol_id:
            await modal.Volume.delete.aio(label=vol_id)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
