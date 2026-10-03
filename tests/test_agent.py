import asyncio
import dataagent.tools
import pytest
from pydantic import ValidationError
from dataagent.llm import MockLLM
from dataagent.schemas import LLMDecision, ToolCall
from dataagent.registry import registry
from dataagent.agent import Agent, MAX_TURNS
from dataagent.warehouse import EmbeddedWarehouse
from dataagent.tools.query import ExecuteQueryInput
from dataagent.tools.context import SearchContextInput, search_context

@pytest.fixture
def warehouse():
    wh = EmbeddedWarehouse()
    try:
        yield wh
    finally:
        wh.close()

def make_agent(warehouse) -> Agent:
    return Agent(MockLLM(), registry, warehouse)

def test_agent_chat_returns_real_catalog_rows(warehouse):
    response = asyncio.run(make_agent(warehouse).chat("find sales data"))
    assert "sales" in response.answer and response.tools_used == ["search_catalog"]
    assert "customers" in response.tables_used or "orders" in response.tables_used

def test_validation_rejects_bad_args():
    with pytest.raises(ValidationError):
        ExecuteQueryInput.model_validate({"nope": 1})

def test_loop_bounded_on_malformed_call(warehouse):
    response = asyncio.run(make_agent(warehouse).chat("run the query"))
    assert response.answer == "max turns exceeded" and response.turns == MAX_TURNS

class OneQueryLLM:
    # one real execute_query, then stop. MockLLM never does this.
    def __init__(self):
        self.n = 0

    async def select_tool(self, messages, tools):
        self.n += 1
        if self.n == 1:
            return LLMDecision(tool_call=ToolCall(
                name="execute_query",
                arguments={"sql": "SELECT count(*) FROM orders"},
            ))
        return LLMDecision()

def test_answer_carries_sql(warehouse):
    response = asyncio.run(Agent(OneQueryLLM(), registry, warehouse).chat("how many orders"))
    assert response.sql == "SELECT count(*) FROM orders"
    assert response.tools_used == ["execute_query"]

class BadSqlLLM:
    def __init__(self):
        self.seen = []

    async def select_tool(self, messages, tools):
        self.seen.append(list(messages))
        if len(self.seen) == 1:
            return LLMDecision(tool_call=ToolCall(
                name="execute_query",
                arguments={"sql": "SELECT * FROM missing_table"},
            ))
        return LLMDecision(text="stopped")

def test_bad_sql_is_fed_back_instead_of_raising(warehouse):
    llm = BadSqlLLM()
    response = asyncio.run(Agent(llm, registry, warehouse).chat("nope"))
    assert response.answer == "stopped"
    assert response.tools_used == []
    feedback = [m.content for m in llm.seen[1] if m.role == "system"]
    assert feedback and "missing_table" in feedback[-1]

def test_context_tool_hits_revenue():
    result = asyncio.run(search_context(SearchContextInput(keyword="revenue"), warehouse=None))
    assert result["hits"]
    assert any("completed" in h["snippet"] for h in result["hits"])
