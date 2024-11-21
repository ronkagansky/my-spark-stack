import datetime
import re
from typing import Tuple

from config import FAST_MODEL, MAIN_MODEL, FAST_PROVIDER
from agents.providers import LLM_PROVIDERS


async def chat_complete(
    system_prompt: str,
    user_prompt: str,
    fast: bool = True,
    temperature: float = 0.0,
) -> str:
    model = FAST_MODEL if fast else MAIN_MODEL
    return await LLM_PROVIDERS[FAST_PROVIDER]().chat_complete(
        system_prompt, user_prompt, model, temperature
    )


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
