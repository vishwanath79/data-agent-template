from dataclasses import dataclass
from typing import Callable
from pydantic import BaseModel
from dataagent.schemas import ToolInfo

class UnknownTool(Exception): ...

@dataclass
class Tool:
    name: str
    description: str
    category: str
    input_schema: type[BaseModel]
    handler: Callable

class Registry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        if name not in self._tools:
            raise UnknownTool(f"unknown tool: {name}")
        return self._tools[name]

    def list_tools(self) -> list[ToolInfo]:
        return [
            ToolInfo(
                name=t.name,
                description=t.description,
                category=t.category,
                parameters=t.input_schema.model_json_schema(),
            )
            for t in self._tools.values()
        ]

registry = Registry()

def tool(name: str, description: str, category: str, input_schema: type[BaseModel]):
    def decorator(handler: Callable) -> Callable:
        registry.register(Tool(name, description, category, input_schema, handler))
        return handler
    return decorator
