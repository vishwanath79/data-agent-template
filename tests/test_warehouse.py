import asyncio
import pytest
from dataagent.warehouse import EmbeddedWarehouse, WarehouseError, _ident

@pytest.fixture
def warehouse():
    wh = EmbeddedWarehouse()
    try:
        yield wh
    finally:
        wh.close()

def test_csvs_load(warehouse):
    result = asyncio.run(warehouse.execute("SELECT count(*) FROM orders"))
    assert result.rows[0][0] == 50

def test_warehouse_refuses_writes(warehouse):
    with pytest.raises(WarehouseError):
        asyncio.run(warehouse.execute("DROP TABLE orders"))

def test_dry_run_counts_the_table_not_a_substring(warehouse):
    # "orders" is inside "preorders". That must not add the orders row count.
    est = asyncio.run(warehouse.dry_run(
        "SELECT * FROM customers WHERE name <> 'preorders'"
    ))
    assert est.scanned_rows == 20

def test_identifier_must_be_a_plain_name():
    with pytest.raises(ValueError):
        _ident("orders; DROP TABLE orders")

def test_scratch_file_is_removed_on_close():
    wh = EmbeddedWarehouse()
    path = wh._scratch
    assert path.exists()
    wh.close()
    assert not path.exists()
