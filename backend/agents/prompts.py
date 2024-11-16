from openai import AsyncOpenAI
import datetime
import re
import os


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


async def name_chat(seed_prompt: str) -> str:
    system_prompt = """
You are helping name a project and a session for a user building an app.

Given the initial prompt a user used to start the project, generate a name for the project and a name for the session.

Project name should be a short name for the app (be creative but concise).

Session name should be a short name for the user's current task (be creative but concise).

Respond only in the following format:
<output-format>
project: ...
session: ...
</output-format>

<example>
project: Astro App
session: Build the UI for Astro App
</example>
"""
    user_prompt = seed_prompt
    content = await chat_complete(system_prompt, user_prompt)
    try:
        project, session = re.search(r"project: (.*)\nsession: (.*)", content).groups()
    except Exception:
        print(f"Invalid response format: {content}")
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        project, session = f"Project {date}", f"Chat {date}"
    return project, session
