from openai import AsyncOpenAI
import datetime
import re
import os
from typing import Tuple

oai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FAST_MODEL = os.getenv("OPENAI_FAST_MODEL", "gpt-4o-mini")
MAIN_MODEL = os.getenv("OPENAI_MAIN_MODEL", "gpt-4o")


async def chat_complete(
    system_prompt: str,
    user_prompt: str,
    model: str = FAST_MODEL,
    temperature: float = 0.0,
) -> str:
    resp = await oai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content


async def name_chat(seed_prompt: str) -> Tuple[str, str, str]:
    system_prompt = """
You are helping name a project and a session for a user building an app.

Given the initial prompt a user used to start the project, generate a name for the project and a name for the session.

Project name should be a short name for the app (be creative but concise).

Project description should be a short description/pitch of the app and what it aims to do (be creative but keep ~1 sentence).

Session name should be a short name for the user's current task (be creative but concise).

Respond only in the following format:
<output-format>
project: ...
project-description: ...
session: ...
</output-format>

<example>
project: Astro App
project-description: An app to empower astronomers to track celestial events.
session: Build the UI for Astro App
</example>
"""
    user_prompt = seed_prompt
    content = await chat_complete(system_prompt, user_prompt)
    try:
        project, project_description, session = re.search(
            r"project: (.*)\nproject-description: (.*)\nsession: (.*)", content
        ).groups()
    except Exception:
        print(f"Invalid response format: {content}")
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        project, project_description, session = (
            f"Project {date}",
            f"A project created on{date}",
            f"Chat {date}",
        )
    return project, project_description, session


async def write_commit_message(content: str) -> str:
    return await chat_complete(
        "You are a helpful assistant that writes commit messages for git. Given the following changes, write a commit message for the changes. Respond only with the commit message. Do not use quotes or special characters.",
        content[:100000],
    )


async def apply_smart_diff(original_content: str, diff: str) -> str:
    return await chat_complete(
        "You are a senior software engineer that applies code changes to a file. Given the original content and the diff, apply the changes to the content. Respond only with the updated content (no code blocks or other formatting).",
        f"<original-content>\n{original_content}\n</original-content>\n\n<diff>\n{diff}\n</diff>",
    )
