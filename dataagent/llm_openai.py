import json
import os
from openai import AsyncOpenAI
from dataagent.schemas import LLMDecision, Message, ToolCall, ToolInfo
DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

class OpenAICompatLLM:
    def __init__(self):
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("set OPENAI_API_KEY before USE_LLM=1")
        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE),
            api_key=key,
        )
        self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    async def select_tool(self, messages: list[Message], tools: list[ToolInfo]) -> LLMDecision:
        payload = [
            {
                "role": "system",
                "content": (
                    "You are a data agent. Use tools to find tables, read metric definitions, "
                    "dry-run SQL, then execute it. When you have enough, answer in plain English."
                ),
            }
        ]
        for m in messages:
            if m.role == "user":
                payload.append({"role": "user", "content": m.content})
            else:
                # tool JSON and validation errors. A system role mid-chat is
                # rejected by some OpenAI-compatible servers.
                label = "Tool result" if m.role == "tool" else "Note"
                payload.append({"role": "user", "content": f"{label}:\n{m.content}"})

        specs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=payload,
            tools=specs or None,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            args = tc.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            return LLMDecision(tool_call=ToolCall(name=tc.function.name, arguments=args or {}))
        return LLMDecision(text=msg.content)
