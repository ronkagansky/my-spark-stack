import datetime
import re
from typing import List, Tuple

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


async def pick_stack(seed_prompt: str, stack_titles: List[str], default: str) -> str:
    system_prompt = f"""
You are a helpful full-stack developer helping advise a user on which stack to use.

Stacks: {stack_titles}

User prompt: {repr(seed_prompt)}

Tips:
- Strongly lean towards `Next.js Shadcn` for apps, websites, etc.
- Strongly lean towards `p5.js` for generative art, games, simulations, etc.
- Use other stacks unless theirs a very clear reason to not use Shadcn or p5.js

Describe what they might need briefly and then pick the stack that best fits their needs.

<output-format>
reasoning: ...
stack: ...
</output-format>

Respond with <output-format> without the tags.
"""
    content = await chat_complete(system_prompt, seed_prompt)
    try:
        # Extract stack from response
        stack = re.search(r"stack: (.*)", content).group(1).strip()
        # Create a mapping of normalized titles to original titles
        stack_map = {title.lower().replace(" ", ""): title for title in stack_titles}
        # Try to find the stack in our normalized mapping
        normalized_input = stack.lower().replace(" ", "")
        return stack_map.get(normalized_input, default)
    except Exception:
        return default
