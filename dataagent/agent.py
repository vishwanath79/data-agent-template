import json
from pydantic import ValidationError
from dataagent.schemas import AgentResponse, Message
from dataagent.registry import Registry, UnknownTool
from dataagent.warehouse import WarehouseError

MAX_TURNS = 8

class Agent:
    def __init__(self, llm, registry: Registry, warehouse=None):
        self.llm = llm
        self.registry = registry
        self.warehouse = warehouse

    async def chat(self, message: str) -> AgentResponse:
        messages = [Message(role="user", content=message)]
        tools_used: list[str] = []

        for turn in range(MAX_TURNS):
            decision = await self.llm.select_tool(messages, self.registry.list_tools())
            if decision.tool_call is None:
                return self._respond(messages, turn + 1, tools_used, answer=decision.text)

            call = decision.tool_call
            try:
                tool = self.registry.get_tool(call.name)
                args = tool.input_schema.model_validate(call.arguments)
                result = await tool.handler(args, self.warehouse)
            except (UnknownTool, ValidationError) as e:
                messages.append(Message(role="system", content=f"error: {self._error_line(e)}"))
                continue
            except WarehouseError as e:
                # bad SQL and refused writes. A KeyError in a tool still crashes.
                messages.append(Message(role="system", content=f"error: {type(e).__name__}: {e}"))
                continue

            messages.append(Message(
                role="tool",
                content=json.dumps({"tool": call.name, **result}, default=str),
            ))
            tools_used.append(call.name)

        return AgentResponse(answer="max turns exceeded", turns=MAX_TURNS, tools_used=tools_used)

    def _respond(self, messages: list[Message], turns: int, tools_used: list[str], answer: str | None = None) -> AgentResponse:
        sql, tables_used = self._evidence(messages)
        if answer:
            text = answer
        elif tools_used:
            text = next(m.content for m in reversed(messages) if m.role == "tool")
        else:
            errors = [m.content for m in messages if m.role == "system"]
            text = f"I could not complete that: {errors[-1]}" if errors else \
                "Hello. Try asking me to find sales data."
        return AgentResponse(answer=text, turns=turns, tools_used=tools_used, sql=sql, tables_used=tables_used)

    @staticmethod
    def _evidence(messages: list[Message]) -> tuple[str | None, list[str]]:
        sql = None
        tables: list[str] = []
        for m in messages:
            if m.role != "tool":
                continue
            try:
                data = json.loads(m.content)
            except json.JSONDecodeError:
                continue
            if "estimate" in data and isinstance(data["estimate"], dict):
                sql = data["estimate"].get("sql") or sql
            if data.get("sql"):
                sql = data["sql"]
            if "tables" in data and isinstance(data["tables"], list):
                tables = [t["name"] for t in data["tables"] if isinstance(t, dict) and t.get("name")]
            elif "datasets" in data and isinstance(data["datasets"], list):
                nested = []
                for d in data["datasets"]:
                    if not isinstance(d, dict):
                        continue
                    nested.extend(d.get("tables") or [])
                    if d.get("name") and not nested:
                        nested.append(d["name"])
                if nested:
                    tables = nested
        return sql, tables

    @staticmethod
    def _error_line(e: Exception) -> str:
        if isinstance(e, UnknownTool):
            return str(e)
        return f"invalid arguments: {e.errors()[0]['loc'][0]}: {e.errors()[0]['msg']}"
