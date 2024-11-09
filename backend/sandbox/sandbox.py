import modal

app = modal.App.lookup("prompt-stack-sandbox", create_if_missing=True)

image = (
    modal.Image.debian_slim()
    .run_commands("apt-get update")
    .run_commands("apt-get install -y --no-install-recommends curl")
    .run_commands("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -")
    .run_commands("apt-get install -y --no-install-recommends nodejs")
    .run_commands("node --version && npm --version")
)
image_start_cmd = """
cd /app && if [ ! -d "my-app" ]; then npx --yes create-react-app my-app; fi && cd my-app && npm start
""".strip()


class DevSandbox:
    def __init__(self, project_id: int, sb: modal.Sandbox):
        self.project_id = project_id
        self.sb = sb

    @classmethod
    async def get_or_create(cls, project_id: int):
        sandboxes = [
            sandbox
            async for sandbox in modal.Sandbox.list.aio(
                app_id=app.app_id,
                tags={"project_id": str(project_id)},
            )
        ]
        if len(sandboxes) == 0:
            vol = modal.Volume.from_name(
                f"vol-project-{project_id}", create_if_missing=True
            )
            sb = await modal.Sandbox.create.aio(
                "sh",
                "-c",
                image_start_cmd,
                app=app,
                volumes={"/app": vol},
                image=image,
                encrypted_ports=[3000],
                timeout=3600,
                cpu=1,
                memory=512,
            )
            await sb.set_tags.aio({"project_id": str(project_id)})
        else:
            sb = sandboxes[0]
        return cls(project_id, sb)
