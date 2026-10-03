from pathlib import Path
from pydantic import BaseModel
from dataagent.registry import tool

CONTEXT_DIR = Path(__file__).resolve().parent.parent / "context"

class SearchContextInput(BaseModel):
    keyword: str

@tool(
    name="search_context",
    description="Search metric definitions and dataset notes. Use when the user asks what a metric means, which tables to join, or what is in or out of scope.",
    category="context",
    input_schema=SearchContextInput,
)
async def search_context(args: SearchContextInput, warehouse) -> dict:
    needle = args.keyword.lower()
    hits = []
    for path in sorted(CONTEXT_DIR.glob("*.md")):
        text = path.read_text()
        if needle not in text.lower() and needle not in path.stem.lower():
            continue
        hits.append({"path": path.name, "snippet": text.strip()})
    return {"hits": hits}
