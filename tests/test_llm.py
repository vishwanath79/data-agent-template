import asyncio
from dataagent.llm import MockLLM
from dataagent.schemas import Message

def test_mock_llm_maps_find_sales_data():
    decision = asyncio.run(MockLLM().select_tool([Message(role="user", content="find sales data")], []))
    assert decision.tool_call is not None and decision.tool_call.name == "search_catalog"

def test_mock_llm_maps_revenue_to_context():
    decision = asyncio.run(MockLLM().select_tool([Message(role="user", content="what does revenue mean")], []))
    assert decision.tool_call is not None and decision.tool_call.name == "search_context"
