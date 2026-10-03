import pytest
from pydantic import BaseModel
from dataagent.registry import Registry, UnknownTool, Tool

class In(BaseModel):
    keyword: str

async def stub(args, warehouse):
    return {}

def test_register_and_lookup():
    r = Registry()
    r.register(Tool("echo", "stub", "data_discovery", In, stub))
    assert r.get_tool("echo").name == "echo"
    assert r.list_tools()[0].name == "echo"

def test_unknown_tool_raises():
    with pytest.raises(UnknownTool):
        Registry().get_tool("nope")