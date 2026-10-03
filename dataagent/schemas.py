from pydantic import BaseModel

class Message(BaseModel):
    role: str      # "user" | "tool" | "system"
    content: str

class ToolCall(BaseModel):
    name: str
    arguments: dict

class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    parameters: dict = {}   # input_schema.model_json_schema(), for the LLM menu

class LLMDecision(BaseModel):
    tool_call: ToolCall | None = None
    text: str | None = None

class AgentResponse(BaseModel):
    answer: str
    turns: int
    tools_used: list[str]
    sql: str | None = None
    tables_used: list[str] = []

class DatasetInfo(BaseModel):
    name: str
    description: str
    owner: str
    tables: list[str]

class TableInfo(BaseModel):
    name: str
    columns: list[str]

class CostEstimate(BaseModel):
    sql: str
    scanned_rows: int

class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list]
