from pydantic import BaseModel
from typing import AsyncGenerator, List, Optional
import re
import json

from db.models import Project, Stack
from sandbox.sandbox import DevSandbox
from agents.prompts import (
    chat_complete,
)
from config import MAIN_MODEL, MAIN_PROVIDER
from agents.diff import remove_file_changes
from agents.providers import AgentTool, LLM_PROVIDERS


class ChatMessage(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    images: Optional[List[str]] = None


class PartialChatMessage(BaseModel):
    role: str
    delta_content: str = ""
    delta_thinking_content: str = ""


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
        name="run_command",
        description="Run a shell command in the project sandbox. Use for installing packages or reading the content of files. NEVER use to modify the content of files.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "workdir": {
                    "type": "string",
                    "description": "The directory to run the command in. Defaults to /app and most of the time that's what you want.",
                },
            },
            "required": ["command"],
        },
        func=func,
    )


def build_navigate_to_tool(agent: "Agent"):
    async def func(path: str):
        agent.working_page = path
        print(f"Navigating user to {path}")
        return "Navigating user to " + path

    return AgentTool(
        name="navigate_to",
        description="Trigger the user's browser to navigate to the given path (e.g. /settings)",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
        func=func,
    )


SYSTEM_PLAN_PROMPT = """
You are a full-stack export developer on the platform Prompt Stack. You are given a project and a sandbox to develop in and are helping PLAN the next steps. You do not write code and only provide advice as a Senior Engineer.

They will be able to edit files, run arbitrary commands in the sandbox, and navigate the user's browser.

<project>
{project_text}
</project>

<stack>
{stack_text}
</stack>

<project-files>
{files_text}
</project-files>

Answer the following questions:
1. What is being asked by the most recent message?
1a. Is this a general question, command to build something, etc.?
2. Which files are relevant to the question or would be needed to perform the request?
2a. What page should the user be navigated to to see/verify the change? (e.g. /settings since we are working on that page)
3. What commands might you need to run?
3a. What packages need to be installed?
4. For EACH stack-specific tip, what do you need to keep in mind or how does this adjust your plan?
5. Finally, what are the full sequence of steps to take to answer the question? (tools/commands -> generate files -> conclusion)
5a. What commands should we run?
5b. What files should we cat to see what we have?
5c. What high level changes do you need to make to the files?
5d. Be specific about how it should be done based on the stack and project notes.
5e. Add a reminder they should use the `simple-code-block-template` to format their code.
6. Verify your plan makes sense given the stack and project. Make any adjustments as needed.

Output you response in markdown (not with code block) using "###" for brief headings and your plan/answers in each section.

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
You are a full-stack export developer on the platform Prompt Stack. You are given a <project> and a <stack> sandbox to develop in and a <plan> from a senior engineer.

<commands>
You are able run shell commands in the sandbox.

- This includes common tools like `npm`, `cat`, `ls`, `git`, etc. avoid any commands that require a GUI or interactivity.
- DO NOT USE TOOLS to modify the content of files. You also do not need to display the commands you use.
- DO NOT use `touch`, `vim`, `nano`, etc.

You must use the proper tool calling syntax to actually execute the command (even if you haven't done this for previous steps).
</commands>

<formatting-instructions>
You'll respond in plain markdown for a chat interface and use special codeblocks for coding and updating files. Generally keep things brief.

YOU must use well formatted simplified code blocks to update files.
- The first line of the code block MUST be a comment with only the full path to the file
- ONLY put code and comments within code blocks. Do not add additional indentation to the code blocks (``` should be at the start of the line).
- Please output a version of the code block that highlights the changes necessary and adds comments to indicate where unchanged code has been skipped.
- Keep in mind the project, stack, and plan instructions as you write the code.

<simple-code-block-template>
```language
// /path/to/file.ext
// ... existing code ...
{{ edit_1 }}
// ... existing code ...
{{ edit_2 }}
// ... existing code ...
```
</simple-code-block-template>

You should literally output "... existing code ..." and write actual code in place of the {{ edit_1 }} and {{ edit_2 }} sections.
</formatting-instructions>

<project>
{project_text}
</project>

<stack>
{stack_text}
</stack>

<project-files>
{files_text}
</project-files>

<plan>
{plan_text}
</plan>

<tips>
- When you use these code blocks the system will automatically apply the file changes (do not also use tools to do the same thing).
- This apply will happen after you've finished your response and automatically include a git commit of all changes.
- No need to run `npm run dev`, etc since the sandbox will handle that.
</tips>

Follow the <plan>.
"""

SYSTEM_FOLLOW_UP_PROMPT = """
You are a full-stack developer helping someone build a webapp.

You are given a conversation between the user and the assistant for building <project> on <stack>.

Your job is to suggest 3 follow up prompts that the user is likely to ask next.

<output-format>
 - ...prompt...
 - ...prompt...
 - ...prompt...
</output-format>

<example>
 - Add a settings page
 - Improve the styling of the homepage
 - Add more dummy content
</example>

Notice these are content based and are written as commands. Do not propose questions not related to the "product" being built like devops, etc.

Keep the questions brief (~at most 10 words) and PERSONALIZED to the most recent asks in the conversation. Do not use ANY text formatting and respond in plain text.

<project>
{project_text}
</project>

<stack>
{stack_text}
</stack>
"""


def _parse_follow_ups(content: str) -> List[str]:
    return re.findall(r"\s*\-\s*(.+)", content)


class Agent:
    def __init__(self, project: Project, stack: Stack):
        self.project = project
        self.stack = stack
        self.sandbox = None
        self.working_page = None

    def set_sandbox(self, sandbox: DevSandbox):
        self.sandbox = sandbox

    async def _handle_tool_call(self, tools: List[AgentTool], tool_call) -> str:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        tool = next((tool for tool in tools if tool.name == tool_name), None)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await tool.func(**arguments)

    def _get_project_text(self) -> str:
        return f"Name: {self.project.name}\nSandbox Status: {'Ready' if self.sandbox else 'Booting...'}\nCustom Instructions: {self.project.custom_instructions}".strip()

    async def suggest_follow_ups(self, messages: List[ChatMessage]) -> List[str]:
        conversation_text = "\n\n".join(
            [f"<{m.role}>{remove_file_changes(m.content)}</{m.role}>" for m in messages]
        )
        project_text = self._get_project_text()
        system_prompt = SYSTEM_FOLLOW_UP_PROMPT.format(
            project_text=project_text,
            stack_text=self.stack.prompt,
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
        stack_text: str,
        files_text: str,
    ) -> AsyncGenerator[PartialChatMessage, None]:
        conversation_text = "\n\n".join(
            [f"<msg>{remove_file_changes(m.content)}</msg>" for m in messages]
        )
        images = []
        for m in messages[:-2]:
            if m.images:
                images.extend(m.images)
        system_prompt = SYSTEM_PLAN_PROMPT.format(
            project_text=project_text,
            stack_text=stack_text,
            files_text=files_text,
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

    async def _run_command_only_step(self, command: str) -> AsyncGenerator[str, None]:
        if not self.sandbox:
            yield PartialChatMessage(
                role="assistant",
                delta_content="Sandbox is still booting! Try again later.",
            )
            return
        yield PartialChatMessage(
            role="assistant", delta_content=f"Running `{command}`...\n```\n"
        )
        async for chunk in self.sandbox.run_command_stream(command):
            yield PartialChatMessage(role="assistant", delta_content=chunk)
        yield PartialChatMessage(role="assistant", delta_content="\n```")

    async def step(
        self,
        messages: List[ChatMessage],
        sandbox_file_paths: Optional[List[str]] = None,
    ) -> AsyncGenerator[PartialChatMessage, None]:
        yield PartialChatMessage(role="assistant", delta_content="")

        # just run the command and return the output
        if messages[-1].role == "user" and messages[-1].content.startswith("$ "):
            async for chunk in self._run_command_only_step(messages[-1].content[2:]):
                yield chunk
            return

        if sandbox_file_paths is not None:
            files_text = "\n".join(sandbox_file_paths)
        else:
            files_text = "Sandbox is still booting..."
        project_text = self._get_project_text()
        stack_text = self.stack.prompt

        plan_content = ""
        async for chunk in self._plan(messages, project_text, stack_text, files_text):
            yield chunk
            plan_content += chunk.delta_thinking_content

        system_prompt = SYSTEM_EXEC_PROMPT.format(
            project_text=project_text,
            stack_text=stack_text,
            files_text=files_text,
            plan_text=plan_content,
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
        tools = [build_run_command_tool(self.sandbox), build_navigate_to_tool(self)]

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
            elif chunk["type"] == "tool_calls":
                yield PartialChatMessage(role="assistant", delta_content="\n\n")
