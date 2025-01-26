from pydantic import BaseModel
import re
import asyncio
import os

from sandbox.sandbox import DevSandbox
from agents.prompts import chat_complete


def _extract_code_block(content: str) -> str:
    """Extract code from a markdown code block, handling both ```...``` and ```language...``` formats."""
    # Match code blocks with or without language specification
    pattern = r"```(?:\w+\n)?([\s\S]+?)```"
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip()
    return content.strip()


_CODE_BLOCK_PATTERNS = [
    r"```[\w.]+\n[#/]+ (\S+)\n([\s\S]+?)```",  # Python-style comments (#)
    r"```[\w.]+\n[/*]+ (\S+) \*/\n([\s\S]+?)```",  # C-style comments (/* */)
    r"```[\w.]+\n<!-- (\S+) -->\n([\s\S]+?)```",  # HTML-style comments <!-- -->
]

_DIFF_TIPS = {
    r"<Link[^>]*>[\S\s]*?<a[^>]*>": "All <Link> tags should be free of <a> tags. Remove all <a> tags from <Link> tags.",
    "<CardBody": "Ensure in Shadcn UI, <Card>s use <CardContent> instead of <CardBody>.",
    "<Slider": "Ensure <Slider />s in Shadcn have at least values= or a min= and a max= attribute.",
    r"Layout\(": "Ensure Layouts in Next.js retain <html> and <body> tags.",
    "use-toast": 'Ensure the import is from "@/hooks/use-toast" (rather than components)',
}

_EXT_TO_MARKDOWN_LANGUAGE = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".mjs": "javascript",
    ".mts": "typescript",
}


async def _apply_smart_diff(
    original_content: str, diff: str, tips: str, file_path: str
) -> str:
    _, ext = os.path.splitext(file_path)
    md_lang = _EXT_TO_MARKDOWN_LANGUAGE.get(ext, "")
    output = await chat_complete(
        """
You are a senior software engineer that applies code changes to a file. Given the <original-content>, the <diff>, and the <adjustments>, apply the changes to the content. 

- You must apply the <adjustments> (if provided) even if this conflicts with the original diff
- You must follow instructions from within comments in <diff> (e.g. <!-- remove this -->)
- You must maintain the layout of the file especially in languages/formats where it matters. Carefully preserve imports.
- Ensure you maintain sections of the original file IF the diff denotes them with "... existing code ..." or other similar comment-based instructions
- You must provide the FULL content of the new file. All "... existing code ...", etc should be replaced with the actual content.

Respond ONLY with the updated content in a code block.
""".strip(),
        f"""
{file_path}

<original-content>
```{md_lang}
{original_content}
```
</original-content>

<diff>
```{md_lang}
{diff}
```
</diff>

<adjustments>
{tips}
</adjustments>
""".strip(),
    )
    return _extract_code_block(output)


def remove_file_changes(content: str) -> str:
    for pattern in _CODE_BLOCK_PATTERNS:
        content = re.sub(pattern, "", content)
    return content


class DiffApplier:
    def __init__(self, sandbox: DevSandbox):
        self.sandbox = sandbox
        self.total_content = ""
        self._changed_files = {}  # path -> diff
        self._pending_tasks = {}  # path -> Task
        self._processed_positions = set()  # Set of (file_path, start_pos) tuples

    def ingest(self, content: str):
        self.total_content += content

        for pattern in _CODE_BLOCK_PATTERNS:
            matches = re.finditer(pattern, self.total_content)
            for match in matches:
                file_path = match.group(1)
                diff = match.group(2).strip()
                # Calculate absolute position in total content
                abs_start = match.start()

                # Skip if we've already processed this match
                if (file_path, abs_start) in self._processed_positions:
                    continue

                self._processed_positions.add((file_path, abs_start))
                self._changed_files[file_path] = diff
                # Kickoff async task to compute the smart diff
                self._pending_tasks[file_path] = asyncio.create_task(
                    self._compute_diff(file_path, diff)
                )

    async def _compute_diff(self, file_path: str, diff: str) -> str:
        tips = []
        for pattern, tip in _DIFF_TIPS.items():
            if re.search(pattern, diff):
                tips.append(tip)

        try:
            original_content = await self.sandbox.read_file_contents(file_path)
        except Exception:
            original_content = "(file does not yet exist)"

        skip_conditions = [
            "... (" not in diff,
            "... keep" not in diff,
            "... existing" not in diff,
            "... rest" not in diff,
            "the same..." not in diff,
            len(tips) == 0,
        ]
        if all(skip_conditions):
            print(f"Writing {file_path} directly...")
            full_content = diff
        else:
            print(f"Writing {file_path} smart diff...")
            full_content = await _apply_smart_diff(
                original_content, diff, "\n".join([f" - {t}" for t in tips]), file_path
            )
        await self.sandbox.write_file(file_path, full_content)

    async def apply(self):
        """Wait for all pending diffs to complete and return the changes."""
        if not self._pending_tasks:
            return []

        # Wait for all pending tasks to complete
        results = await asyncio.gather(
            *self._pending_tasks.values(), return_exceptions=True
        )
        for (file_path, task), result in zip(self._pending_tasks.items(), results):
            if isinstance(result, Exception):
                print(f"Error processing {file_path}: {result}")
