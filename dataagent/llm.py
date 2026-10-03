from typing import Protocol
from dataagent.schemas import LLMDecision, Message, ToolCall, ToolInfo

class LLMBackend(Protocol):
    async def select_tool(self, messages: list[Message], tools: list[ToolInfo]) -> LLMDecision: ...

# most-specific first: "revenue"/"definition" before "sales", "cost"/"estimate" before "run"
RULES = [
    (("revenue", "definition", "mean"), "search_context", {"keyword": "revenue"}),
    (("sales",), "search_catalog", {"keyword": "sales"}),
    (("tables",), "list_tables", {"dataset": "sales"}),
    (("cost", "estimate"), "validate_query", {"sql": "SELECT * FROM orders"}),
    (("run",), "execute_query", {}),   # deliberately malformed: missing sql
]

class MockLLM:
    async def select_tool(self, messages: list[Message], tools: list[ToolInfo]) -> LLMDecision:
        if messages and messages[-1].role == "tool":
            return LLMDecision()
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        lowered = last_user.lower()
        for keywords, name, args in RULES:
            if any(k in lowered for k in keywords):
                return LLMDecision(tool_call=ToolCall(name=name, arguments=dict(args)))
        return LLMDecision()
