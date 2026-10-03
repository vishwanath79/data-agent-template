from pydantic import BaseModel
from dataagent.registry import tool
from dataagent.warehouse import WarehouseBackend

class ValidateQueryInput(BaseModel):
    sql: str

class ExecuteQueryInput(BaseModel):
    sql: str

@tool(
    name="validate_query",
    description="Dry-run a SQL query: parse it and estimate how many rows it would scan, without running it. Use before execute_query when the user wants a cost or sanity check.",
    category="query_execution",
    input_schema=ValidateQueryInput,
)
async def validate_query(args: ValidateQueryInput, warehouse: WarehouseBackend) -> dict:
    est = await warehouse.dry_run(args.sql)
    return {"estimate": est.model_dump()}

@tool(
    name="execute_query",
    description="Run a SQL query against the warehouse and return at most 10 rows. The warehouse is read-only; only SELECTs succeed. Requires the full SQL text.",
    category="query_execution",
    input_schema=ExecuteQueryInput,
)
async def execute_query(args: ExecuteQueryInput, warehouse: WarehouseBackend) -> dict:
    result = await warehouse.execute(args.sql)
    return {"query_result": result.model_dump(), "sql": args.sql}
