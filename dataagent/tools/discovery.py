from pydantic import BaseModel
from dataagent.registry import tool
from dataagent.warehouse import WarehouseBackend

class SearchCatalogInput(BaseModel):
    keyword: str

class ListTablesInput(BaseModel):
    dataset: str

@tool(
    name="search_catalog",
    description="Find datasets in the data catalog whose name or description matches a keyword. Use this first when the user is looking for data on a topic.",
    category="data_discovery",
    input_schema=SearchCatalogInput,
)
async def search_catalog(args: SearchCatalogInput, warehouse: WarehouseBackend) -> dict:
    return {"datasets": [d.model_dump() for d in await warehouse.search_catalog(args.keyword)]}

@tool(
    name="list_tables",
    description="List the tables and their columns inside a known dataset, e.g. sales. Use after search_catalog when the user wants to explore a dataset's contents.",
    category="data_discovery",
    input_schema=ListTablesInput,
)
async def list_tables(args: ListTablesInput, warehouse: WarehouseBackend) -> dict:
    return {"tables": [t.model_dump() for t in await warehouse.list_tables(args.dataset)]}