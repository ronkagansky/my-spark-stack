from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from config import OPENAI_API_KEY, ANTHROPIC_API_KEY


class LLMProvider(ABC):
    @abstractmethod
    async def chat_complete(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> str:
        pass


class OpenAILLMProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def chat_complete(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> str:
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content


class AnthropicLLMProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    async def chat_complete(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> str:
        resp = await self.client.messages.create(
            model=model,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            system=system_prompt,
        )
        return resp.content[0].text


CHAT_COMPLETION_PROVIDERS = {
    "openai": OpenAILLMProvider,
    "anthropic": AnthropicLLMProvider,
}
