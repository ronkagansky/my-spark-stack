from pydantic import BaseModel
from typing import AsyncGenerator, List, Optional, Dict
import re
import json
import asyncio

from db.models import Project, Stack, User, UserType
from sandbox.sandbox import DevSandbox
from sandbox.browser import BrowserMonitor
from agents.third_party_docs import DOCS
from agents.prompts import (
    chat_complete,
)
from config import MAIN_MODEL, MAIN_PROVIDER
from agents.diff import remove_file_changes, AsyncArtifactDiffApplier
from agents.providers import AgentTool, LLM_PROVIDERS


USER_TYPE_STYLES: Dict[UserType, str] = {
    UserType.WEB_DESIGNER: """User Type: Web Designer
Experience: Familiar with web design concepts and basic HTML/CSS
Communication Style: Use design/UI/UX terminology. Explain technical concepts visually. Be concise. Do not walkthrough all the changes.
Code Explanations: Focus on visual impact and provide context for backend changes. Keep explanations brief.""",
    UserType.LEARNING_TO_CODE: """User Type: Learning to Code
Experience: Basic programming knowledge, learning fundamentals
Communication Style: Break down complex concepts with simple terms. Keep explanations concise. Do not walkthrough all the changes.
Code Explanations: Include brief instructional commentary. Highlight patterns and practices.""",
    UserType.EXPERT_DEVELOPER: """User Type: Expert Developer
Experience: Proficient in full-stack development
Communication Style: Use technical terminology. Focus on architecture and implementation details. Be concise. Do not walkthrough all the changes.
Code Explanations: Skip basics. Highlight advanced patterns and potential edge cases. Keep explanations brief.""",
}

NL = "\n"


class ChatMessage(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    images: Optional[List[str]] = None


class PartialChatMessage(BaseModel):
    role: str
    delta_content: str = ""
    delta_thinking_content: str = ""
    persist: bool = True


def build_run_command_tool(sandbox: Optional[DevSandbox] = None):
    async def func(command: str, workdir: Optional[str] = None) -> str:
        if sandbox is None:
            return "This environment is still booting up! Try again in a minute."
        result = await sandbox.run_command(command, workdir=workdir)
        print(f"$ {command} -> {result[:20]}")
        if result == "":
            result = "<empty response>"
        return result

    return AgentTool(
        name="run_shell_cmd",
        description="Run a shell command in the project sandbox. Use for installing packages or reading the content of files. NEVER use to modify the content of files (`touch`, `vim`, `nano`, etc.).",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to run.",
                },
                "workdir": {
                    "type": "string",
                    "description": "The directory to run the command in. Defaults to /app and most of the time that's what you want.",
                },
            },
            "required": ["command"],
        },
        func=func,
    )


def build_screenshot_and_get_logs_tool(agent: "Agent"):
    async def func(path: str) -> str:
        """Take a screenshot of the specified path."""
        if not agent.sandbox or not agent.app_temp_url:
            return "Sandbox or preview URL is not yet ready. Try again in a minute."

        browser = BrowserMonitor.get_instance()
        page_status = await browser.check_page(
            f"{agent.app_temp_url}{path}",
            wait_time=3,  # Wait a bit longer for page to fully load
        )

        if not page_status or not page_status.screenshot:
            return "Failed to capture screenshot"

        return [
            {
                "type": "text",
                "text": f"""Screenshot captured of {path}
                
Error Logs:
{NL.join(page_status.errors) if page_status.errors else "No errors found"}

Console Messages:
{NL.join(page_status.console) if page_status.console else "No console messages found"}""",
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": page_status.screenshot,
                },
            },
        ]

    return AgentTool(
        name="screenshot_and_get_logs",
        description="Take a screenshot of the specified path in the web app and capture browser logs. Returns both the screenshot image and any error/console logs found. Useful for debugging visual and runtime issues.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to take a screenshot of and capture logs from (e.g. /, /settings, /dashboard)",
                },
            },
            "required": ["path"],
        },
        func=func,
    )


def build_apply_changes_tool(
    agent: "Agent", diff_applier: AsyncArtifactDiffApplier, apply_cnt: Dict[str, int]
):
    async def func(navigate_to: str, commit_message: str) -> str:
        """Apply changes, run linting, and check browser for errors."""
        if not agent.sandbox:
            return "Sandbox is not yet ready. Stop and try again after a minute."

        agent.working_page = navigate_to

        # Run these tasks in parallel with gather
        processed_files, has_lint_file = await asyncio.gather(
            diff_applier.apply(), agent.sandbox.has_file("/app/frontend/.eslintrc.json")
        )

        # Prepare the lint check task
        async def run_lint_check():
            if not has_lint_file:
                return "No lint configuration found"
            lint_output = await agent.sandbox.run_command(
                "npm run lint", workdir="/app/frontend"
            )
            return (
                "Error: " + lint_output
                if "Error:" in lint_output
                else "Lint successful!"
            )

        # Prepare the browser check task
        async def run_browser_check():
            if not agent.app_temp_url:
                return "Browser check skipped - no preview URL available", None

            browser = BrowserMonitor.get_instance()
            page_status = await browser.check_page(
                f"{agent.app_temp_url}{agent.working_page or '/'}"
            )

            browser_result = "Browser logs look good!"
            browser_screenshot = None

            if page_status:
                if page_status.errors or page_status.console:
                    browser_result = "\n".join(
                        [f"Error: {err}" for err in page_status.errors]
                    )
                if page_status.screenshot:
                    browser_screenshot = {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": page_status.screenshot,
                        },
                    }
            return browser_result, browser_screenshot

        # Run lint and browser checks in parallel
        lint_result, (browser_result, browser_screenshot) = await asyncio.gather(
            run_lint_check(), run_browser_check()
        )

        # Commit the changes
        await agent.sandbox.commit_changes(commit_message)

        result = [
            {
                "type": "text",
                "text": f"""
Changes applied successfully. All changes live at {agent.app_temp_url}!

<updated-files>
The codeblocks you provided have been applied. Do not provide any more codeblocks unless you intentionally want to update and and later re-apply more changes.
{NL.join(processed_files)}
</updated-files>

<lint-result>
{lint_result}
</lint-result>

<browser-result>
{browser_result}
</browser-result>
""".strip(),
            }
        ]

        if browser_screenshot:
            result.append(browser_screenshot)

        apply_cnt["cnt"] += 1

        return result

    return AgentTool(
        name="apply_changes",
        description="Apply code changes. Runs linting, checks browser logs, git commits all changes. Returns logs and a screenshot of the changes.",
        parameters={
            "type": "object",
            "properties": {
                "navigate_to": {
                    "type": "string",
                    "description": "The page path most relevant to the changes. E.g. /, /settings, /dashboard, etc.",
                },
                "commit_message": {
                    "type": "string",
                    "description": "The commit message to use for the changes. Do not use quotes or special characters. Do not use markdown formatting, newlines, or other formatting. Start with a verb, e.g. 'Fixed', 'Added', 'Updated', etc.",
                },
            },
            "required": ["navigate_to", "commit_message"],
        },
        func=func,
    )


def build_read_docs_tool():
    async def func(page: str) -> str:
        """Read documentation for a specific page."""
        if page not in DOCS:
            return f"Documentation not found for {page}. Available pages: {', '.join(DOCS.keys())}"
        return DOCS[page]

    return AgentTool(
        name="read_docs",
        description="Read documentation for a specific page from the third party docs.",
        parameters={
            "type": "object",
            "properties": {
                "page": {
                    "type": "string",
                    "description": f"The page to read documentation for. Available pages: {', '.join(DOCS.keys())}",
                },
            },
            "required": ["page"],
        },
        func=func,
    )


SYSTEM_PLAN_PROMPT = """
You are a full-stack world class developer on the platform Spark Stack. You are given a project and a sandbox to develop in and are helping PLAN the next steps. You do not write code and only provide advice as a Staff Engineer.

They will be able to edit files, run arbitrary commands in the sandbox, and navigate the user's browser.

<project>
{project_text}
</project>

<user>
{user_text}
</user>

<stack>
{stack_text}
</stack>

<project-files>
{files_text}
</project-files>

<git-log>
{git_log_text}
</git-log>

<tools>
The engineer will have these tools available to them:
- run shell commands (run_shell_cmd)
- take a screenshot and gather logs (screenshot_and_get_logs)
- apply changes, commit them, and gather post-commit logs (apply_changes)
- read third party documentation (read_docs, e.g. {docs_text})
</tools>

Answer the following questions:
1. What is being asked by the most recent message?
1a. Is this a general question, command to build something, etc.?
2. Which files are relevant to the question or would be needed to perform the request?
2a. What page should the user be navigated to to see/verify the change? (e.g. /settings since we are working on that page)
2b. If there's weird behavior, what files should we cat to double check on the contents?
3. What commands, read docs, or other tools might you need to run?
3a. What packages need to be installed?
4. For EACH stack-specific tip, what do you need to keep in mind or how does this adjust your plan?
5. Finally, what are the full sequence of steps to take to answer the question? (tools/commands -> generate files -> conclusion)
5a. What commands, read docs, or other tools should we run?
5b. What files should we cat to see what we have?
5c. What high-level changes do you need to make to the files?
5d. Be specific about how it should be done based on the stack and project notes.
5e. Add a reminder they should use the right code block format to format their code and end with `apply_changes` tool.
6. Verify your plan makes sense given the stack and project. Make any adjustments as needed.
6a. Verify how you will communicate with the <user> based on their knowledge and experience.

Output your response in markdown (not with code block) using "###" for brief headings and your plan/answers in each section.

<example>
### Analyzing your question...

...

### Figuring out what files to edit...

...
</example>

You can customize the heading titles for each section but make them "thinking" related suffixed with "...". Feel free to omit sections if they obviously don't apply.

DO NOT include any code blocks in your response or text outside of the markdown h3 headings. This should be ADVICE ONLY.
"""

SYSTEM_EXEC_PROMPT = """
You are a full-stack world class developer on the platform Spark Stack. You are given a <project> and a <stack> sandbox to develop in and a <plan> from a Staff Engineer.

<project>
{project_text}
</project>

<user>
{user_text}
</user>

<stack>
{stack_text}
</stack>

<shell-commands>
You are able to run shell commands in the sandbox.
- This includes common tools like `npm`, `cat`, `ls`, `git`, etc. avoid any commands that require a GUI or interactivity.
- Pro Tip: `cat` multiple files within the same command.
- You must use the proper tool calling syntax to actually execute the command (even if you haven't in previous steps).
</shell-commands>

<formatting>
You'll respond in plain markdown for a chat interface and use special codeblocks for coding and updating files. Generally keep things brief.

YOU must use well formatted simplified code blocks to update files.
- The first line of the code block MUST be a comment with only the full path to the file
- ONLY put code and comments within code blocks. Do not add additional indentation to the code blocks (``` should be at the start of the line).
- Please output a version of the code block that highlights the changes necessary and adds comments to indicate where unchanged code has been skipped.
- Keep in mind the project, stack, and plan instructions as you write the code.

Special code block syntax (note absolute path and placeholder comments):
```language
// /path/to/file.ext
// ... existing code ...
{{ edit_1 }}
// ... existing code ...
{{ edit_2 }}
// ... existing code ...
```

- You should literally output comments like "... existing code ..." and write actual code in place of the {{ edit_1 }} and {{ edit_2 }} sections.
- It is also useful to call out large blocks of code you explicitly removed (e.g. "// ... removed code for xyz ...").
- If you are debugging an error, it's useful to be more explicit when fixing the files (using less placeholder comments and more code in these cases).
</formatting>

<tips>
- After you've written our the code changes, you must use the `apply_changes` tool to apply the changes. 
- Do not provide codeblocks after applying changes unless you intentionally want to update the file again.
- This apply will happen after you've finished your response and automatically include a git commit of all changes.
- No need to run `npm run dev`, etc since the sandbox will handle that.
- The Spark Stack UI has built in a "Preview" window of the changes to the right as well as a UI for the user to view/export raw files and config deployment/env variables.
- When providing explanations, do not walkthrough all the changes. Be concise and to the point.
</tips>

Follow the <plan>. End after commiting changes with `apply_changes` tool.
"""

SYSTEM_FOLLOW_UP_PROMPT = """
You are a full-stack developer helping someone build a webapp.

You are given a conversation between the user and the assistant for building <project> on <stack>.

Your job is to suggest 3 follow up prompts that the user is likely to ask next.

<output-format>
<follow-ups>
- ...prompt...
- ...prompt...
- ...prompt...
</follow-ups>
</output-format>

<example>
<follow-ups>
- Add a settings page
- Improve the styling of the homepage
- Add more dummy content
</follow-ups>
</example>

<tips>
- Keep the questions brief (~at most 10 words) and PERSONALIZED to the most recent asks in the conversation.
- Do not propose questions not related to the "product" being built like devops, etc.
- Do not use ANY text formatting and respond in plain text.
</tips>

<project>
{project_text}
</project>

<stack>
{stack_text}
</stack>

Respond with the <follow-ups> section only. Include the <follow-ups> tags.
"""


def _parse_follow_ups(content: str) -> List[str]:
    # Extract content between <follow-ups> tags
    match = re.search(r"<follow-ups>(.*?)</follow-ups>", content, re.DOTALL)
    if not match:
        return []

    # Parse bullet points from the content
    follow_ups = re.findall(r"\s*\-\s*(.+)", match.group(1))
    return follow_ups


def _append_last_user_message(messages: List[dict], text: str) -> List[dict]:
    last_user_message = next(
        (m for m in reversed(messages) if m.get("role") == "user"), None
    )
    if last_user_message:
        if isinstance(last_user_message["content"], list):
            if last_user_message["content"] and isinstance(
                last_user_message["content"][0], dict
            ):
                last_user_message["content"][0]["text"] += "\n\n" + text
            else:
                last_user_message["content"].append({"type": "text", "text": text})
        else:
            last_user_message["content"] += "\n\n" + text
    else:
        raise ValueError("No user message found")


class Agent:
    def __init__(self, project: Project, stack: Stack, user: User):
        self.project = project
        self.stack = stack
        self.user = user
        self.sandbox = None
        self.working_page = None
        self.app_temp_url = None

    def set_sandbox(self, sandbox: DevSandbox):
        self.sandbox = sandbox

    def set_app_temp_url(self, url: str):
        self.app_temp_url = url

    async def _handle_tool_call(self, tools: List[AgentTool], tool_call) -> str:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        tool = next((tool for tool in tools if tool.name == tool_name), None)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await tool.func(**arguments)

    def _get_project_text(self) -> str:
        return f"Name: {self.project.name}\nSandbox Status: {'Ready' if self.sandbox else 'Booting...'}\nCustom Instructions: {self.project.custom_instructions}".strip()

    def _get_user_text(self) -> str:
        """Generate context about the user and how to interact with them based on their user type."""
        return USER_TYPE_STYLES.get(
            self.user.user_type, USER_TYPE_STYLES[UserType.WEB_DESIGNER]
        )

    async def suggest_follow_ups(self, messages: List[ChatMessage]) -> List[str]:
        conversation_text = "\n\n".join(
            [f"<{m.role}>{remove_file_changes(m.content)}</{m.role}>" for m in messages]
        )
        project_text = self._get_project_text()
        stack_text = self.stack.prompt
        system_prompt = SYSTEM_FOLLOW_UP_PROMPT.format(
            project_text=project_text,
            stack_text=stack_text,
        )
        content = await chat_complete(system_prompt, conversation_text[-10000:])
        try:
            return _parse_follow_ups(content)
        except Exception:
            print("Error parsing follow ups", content)
            return []

    async def _plan(
        self,
        messages: List[ChatMessage],
        project_text: str,
        git_log_text: str,
        stack_text: str,
        files_text: str,
        user_text: str,
    ) -> AsyncGenerator[PartialChatMessage, None]:
        conversation_text = "\n\n".join(
            [f"<msg>{remove_file_changes(m.content)}</msg>" for m in messages]
        )
        images = []
        for m in messages[:-2]:
            if m.images:
                images.extend(m.images)

        docs_text = ", ".join(page for page in DOCS.keys())
        system_prompt = SYSTEM_PLAN_PROMPT.format(
            project_text=project_text,
            stack_text=stack_text,
            files_text=files_text,
            git_log_text=git_log_text,
            user_text=user_text,
            docs_text=docs_text,
        )

        # Convert messages to provider format
        planning_messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": conversation_text
                        + "\n\nProvide the plan in the correct format only.",
                    }
                ]
                + (
                    []
                    if not images
                    else [
                        {"type": "image_url", "image_url": {"url": img}}
                        for img in images
                    ]
                ),
            },
        ]

        model = LLM_PROVIDERS[MAIN_PROVIDER]()

        async for chunk in model.chat_complete_with_tools(
            messages=planning_messages,
            tools=[],  # No tools needed for planning
            model=MAIN_MODEL,
            temperature=0.0,
        ):
            if chunk["type"] == "content":
                yield PartialChatMessage(
                    role="assistant", delta_thinking_content=chunk["content"]
                )

    async def _git_log_text(self, git_log: str) -> str:
        git_text = "\n".join(
            [
                f"{items[0]}: {items[1]}"
                for items in [line.split("|") for line in git_log.split("\n") if line]
            ]
        )
        return git_text

    async def step(
        self,
        messages: List[ChatMessage],
        sandbox_file_paths: Optional[List[str]] = None,
        sandbox_git_log: Optional[str] = None,
    ) -> AsyncGenerator[PartialChatMessage, None]:
        yield PartialChatMessage(role="assistant", delta_content="")

        if sandbox_file_paths is not None:
            files_text = "\n".join(sandbox_file_paths)
        else:
            files_text = "Sandbox is still booting."
        if sandbox_git_log is not None:
            git_log_text = await self._git_log_text(sandbox_git_log)
        else:
            git_log_text = "Git log not yet available."
        project_text = self._get_project_text()
        stack_text = self.stack.prompt
        user_text = self._get_user_text()

        plan_content = ""
        async for chunk in self._plan(
            messages, project_text, git_log_text, stack_text, files_text, user_text
        ):
            yield chunk
            plan_content += chunk.delta_thinking_content

        system_prompt = SYSTEM_EXEC_PROMPT.format(
            project_text=project_text,
            stack_text=stack_text,
            user_text=user_text,
        )

        # Convert messages to provider format
        exec_messages = [
            {"role": "system", "content": system_prompt},
            *[
                {
                    "role": message.role,
                    "content": [{"type": "text", "text": message.content}]
                    + (
                        []
                        if not message.images
                        else [
                            {"type": "image_url", "image_url": {"url": img}}
                            for img in message.images
                        ]
                    ),
                }
                for message in messages
            ],
        ]
        _append_last_user_message(
            exec_messages,
            f"---\n<project-files>\n{files_text}\n</project-files>\n<plan>\n{plan_content}\n</plan>\n---",
        )

        diff_applier = AsyncArtifactDiffApplier(self.sandbox)
        apply_cnt = {"cnt": 0}

        tool_cmd = build_run_command_tool(self.sandbox)
        tool_apply = build_apply_changes_tool(self, diff_applier, apply_cnt)
        tool_screenshot_and_get_logs = build_screenshot_and_get_logs_tool(self)
        tool_read_docs = build_read_docs_tool()
        tools = [
            tool_cmd,
            tool_apply,
            tool_screenshot_and_get_logs,
            tool_read_docs,
        ]

        model = LLM_PROVIDERS[MAIN_PROVIDER]()
        async for chunk in model.chat_complete_with_tools(
            messages=exec_messages,
            tools=tools,
            model=MAIN_MODEL,
            temperature=0.0,
        ):
            if chunk["type"] == "content":
                yield PartialChatMessage(
                    role="assistant", delta_content=chunk["content"]
                )
                diff_applier.ingest(chunk["content"])
            elif chunk["type"] == "tool_calls":
                for tool_call in chunk["tool_calls"]:
                    yield PartialChatMessage(
                        role="assistant",
                        persist=False,  # HACK: Show tool calls on UI w/confusing Claude
                        delta_content=f"\n\n```{tool_call['function']['name']}\n# {tool_call['function']['name']}\n{tool_call['function']['arguments']}\n```\n\n",
                    )

        # manually apply if agent forgot to
        if apply_cnt["cnt"] == 0:
            await tool_apply.func(navigate_to="/", commit_message="Several changes")
