from pydantic import BaseModel
from typing import AsyncGenerator, List, Dict, Any, Callable, Optional
import re
import json

from db.models import Project, Stack
from sandbox.sandbox import DevSandbox
from agents.prompts import (
    oai_client,
    chat_complete,
)
from config import OPENAI_FAST_MODEL, OPENAI_MAIN_MODEL
from agents.diff import remove_file_changes


class ChatMessage(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    images: Optional[List[str]] = None


class PartialChatMessage(BaseModel):
    role: str
    delta_content: str = ""
    delta_thinking_content: str = ""


class AgentTool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable

    def to_oai_tool(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


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
        description="Run a command in the project sandbox",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "workdir": {"type": "string"},
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
You are a full-stack export developer on the platform Prompt Stack. You are given a project and a sandbox to develop in and a plan (for the most recent message) from a senior engineer.

<project>
{project_text}
</project>

<stack>
{stack_text}
</stack>

<project-files>
{files_text}
</project-files>

<tools->
<command name="run_command">
You are able run shell commands in the sandbox.

- This includes common tools like `npm`, `cat`, `ls`, `git`, etc. avoid any commands that require a GUI or interactivity.
- DO NOT USE TOOLS to modify the content of files. You also do not need to display the commands you use.
</command>
<command name="navigate_to">
You are able to navigate the user's browser to a given path.
</command>
</tools>

<plan>
{plan_text}
</plan>

<formatting-instructions>
You'll respond in plain markdown for a chat interface and use special codeblocks for coding and updating files. Generally keep things brief.

YOU must use well formatted simplified code blocks to update files.
- The first line of the code block MUST be a comment with only the full path to the file
- ONLY put code and comments within code blocks. Do not add additional indentation to the code blocks (``` should be at the start of the line).
- Please output a version of the code block that highlights the changes necessary and adds comments to indicate where unchanged code has been skipped.
- Keep in mind the project, stack, and plan instructions as you write the code.
- When you use these code blocks the system will automatically apply the file changes (do not also use tools to do the same thing). This apply will happen after you've finished your response and include a git commit of all changes.

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

<example>
I'll now add a main function to the existing file.

```python
# /app/backend/main.py
# ... existing code ...

def main():
    print("Hello, world!")
```

The file has been updated to include the main function.
</example>
</formatting-instructions>
"""

SYSTEM_FOLLOW_UP_PROMPT = """
You are a full-stack developer helping someone build a webapp.

You are given a conversation between the user and the assistant.

Your job is to suggest 3 follow up prompts that the user is likely to ask next.

<project>
{project_text}
</project>

<stack>
{stack_text}
</stack>

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
        stream = await oai_client.chat.completions.create(
            model=OPENAI_FAST_MODEL,
            messages=[
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
            ],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content is not None:
                yield PartialChatMessage(
                    role="assistant", delta_thinking_content=delta.content
                )

    async def step(
        self,
        messages: List[ChatMessage],
        sandbox_file_paths: Optional[List[str]] = None,
    ) -> AsyncGenerator[PartialChatMessage, None]:
        yield PartialChatMessage(role="assistant", delta_content="")

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

        oai_chat = [
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
        running = True

        while running:
            stream = await oai_client.chat.completions.create(
                model=OPENAI_MAIN_MODEL,
                messages=oai_chat,
                tools=[tool.to_oai_tool() for tool in tools],
                stream=True,
            )

            tool_calls_buffer = []
            current_tool_call = None

            async for chunk in stream:
                delta = chunk.choices[0].delta

                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        if tool_call_delta.index is not None:
                            if len(tool_calls_buffer) <= tool_call_delta.index:
                                tool_calls_buffer.append(tool_call_delta)
                                current_tool_call = tool_calls_buffer[
                                    tool_call_delta.index
                                ]
                            else:
                                current_tool_call = tool_calls_buffer[
                                    tool_call_delta.index
                                ]
                                if tool_call_delta.function.name:
                                    current_tool_call.function.name = (
                                        tool_call_delta.function.name
                                    )
                                if tool_call_delta.function.arguments:
                                    if not hasattr(
                                        current_tool_call.function, "arguments"
                                    ):
                                        current_tool_call.function.arguments = ""
                                    current_tool_call.function.arguments += (
                                        tool_call_delta.function.arguments
                                    )

                if chunk.choices[0].finish_reason == "tool_calls":
                    oai_chat.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_buffer,
                        }
                    )
                    for tool_call in tool_calls_buffer:
                        tool_result = await self._handle_tool_call(tools, tool_call)

                        oai_chat.append(
                            {
                                "role": "tool",
                                "content": tool_result,
                                "name": tool_call.function.name,
                                "tool_call_id": tool_call.id,
                            }
                        )
                    yield PartialChatMessage(role="assistant", delta_content="\n")
                elif chunk.choices[0].finish_reason == "stop":
                    running = False
                    break

                if delta.content is not None:
                    yield PartialChatMessage(
                        role="assistant", delta_content=delta.content
                    )
