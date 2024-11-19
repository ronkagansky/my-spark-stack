from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncGenerator, Callable, Type
from pydantic import BaseModel
import json
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from config import OPENAI_API_KEY, ANTHROPIC_API_KEY


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

    def to_anthropic_tool(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters["properties"],
                "required": self.parameters.get("required", []),
            },
        }


class LLMProvider(ABC):
    @abstractmethod
    async def chat_complete(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> str:
        pass

    @abstractmethod
    async def chat_complete_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[AgentTool],
        model: str,
        temperature: float = 0.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        pass

    async def _handle_tool_call(self, tools: List[AgentTool], tool_call) -> str:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        tool = next((tool for tool in tools if tool.name == tool_name), None)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await tool.func(**arguments)


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

    async def chat_complete_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[AgentTool],
        model: str,
        temperature: float = 0.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        oai_tools = [tool.to_oai_tool() for tool in tools]
        running = True
        oai_messages = messages.copy()

        while running:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=oai_messages,
                tools=oai_tools,
                temperature=temperature,
                stream=True,
            )

            tool_calls_buffer = []
            current_tool_call = None

            async for chunk in stream:
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

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

                if finish_reason == "tool_calls":
                    oai_messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_buffer,
                        }
                    )
                    for tool_call in tool_calls_buffer:
                        tool_result = await self._handle_tool_call(tools, tool_call)
                        oai_messages.append(
                            {
                                "role": "tool",
                                "content": tool_result,
                                "name": tool_call.function.name,
                                "tool_call_id": tool_call.id,
                            }
                        )
                    yield {"type": "tool_calls", "tool_calls": tool_calls_buffer}
                elif finish_reason == "stop":
                    running = False
                    break

                if delta.content is not None:
                    yield {"type": "content", "content": delta.content}


class AnthropicLLMProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    async def chat_complete(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> str:
        response = await self.client.messages.create(
            model=model,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            temperature=temperature,
            max_tokens=8192,
        )
        return response.content[0].text

    async def chat_complete_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[AgentTool],
        model: str,
        temperature: float = 0.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # Convert tools to Anthropic format using the new method
        anthropic_tools = [tool.to_anthropic_tool() for tool in tools]

        # Extract system message if present
        system_message = None
        current_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                current_messages.append(msg)

        running = True
        while running:
            # Create base parameters
            create_params = {
                "model": model,
                "messages": current_messages,
                "system": system_message,
                "temperature": temperature,
                "stream": True,
                "max_tokens": 8192,
            }

            # Only add tools and tool_choice if tools are provided
            if tools:
                create_params.update(
                    {"tools": anthropic_tools, "tool_choice": {"type": "any"}}
                )

            stream = await self.client.messages.create(**create_params)

            current_tool_call = None
            content_buffer = ""

            async for chunk in stream:
                if chunk.type == "content_block_start":
                    if chunk.content_block.type == "tool_calls":
                        current_tool_call = {
                            "function": {
                                "name": chunk.content_block.tool_calls[0].name,
                                "arguments": "",
                            }
                        }

                elif chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        content_buffer += chunk.delta.text
                        yield {"type": "content", "content": chunk.delta.text}
                    elif chunk.delta.type == "tool_call_delta":
                        if current_tool_call:
                            current_tool_call["function"][
                                "arguments"
                            ] += chunk.delta.text

                elif chunk.type == "content_block_stop":
                    if current_tool_call:
                        # Handle tool call completion
                        tool_result = await self._handle_tool_call(
                            tools, current_tool_call
                        )
                        yield {"type": "tool_calls", "tool_calls": [current_tool_call]}

                        # Add the assistant's message and tool result to the conversation
                        current_messages.append(
                            {
                                "role": "assistant",
                                "content": content_buffer,
                                "tool_calls": [current_tool_call],
                            }
                        )
                        current_messages.append(
                            {
                                "role": "tool",
                                "content": tool_result,
                                "name": current_tool_call["function"]["name"],
                            }
                        )
                        content_buffer = ""
                        current_tool_call = None
                    else:
                        # No more tool calls, conversation is complete
                        running = False
                        break


LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "openai": OpenAILLMProvider,
    "anthropic": AnthropicLLMProvider,
}
