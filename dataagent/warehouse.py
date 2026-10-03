import atexit
import re
import secrets
from pathlib import Path
from typing import Protocol
import duckdb
from dataagent.schemas import CostEstimate, DatasetInfo, QueryResult, TableInfo

DATA_DIR = Path(__file__).parent / "data"
# table names are interpolated; SQL parameters cannot bind an identifier
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _ident(name: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"bad identifier: {name}")
    return name

class WarehouseError(Exception):
    """The warehouse rejected the SQL. A bug in a tool is not this."""

class WarehouseBackend(Protocol):
    async def search_catalog(self, keyword: str) -> list[DatasetInfo]: ...
    async def list_tables(self, dataset: str) -> list[TableInfo]: ...
    async def dry_run(self, sql: str) -> CostEstimate: ...
    async def execute(self, sql: str) -> QueryResult: ...

class EmbeddedWarehouse:
    def __init__(self):
        import tempfile
        self._closed = False
        self.conn = None
        self._scratch = Path(tempfile.gettempdir()) / f"data-agent-{secrets.token_hex(4)}.db"
        # atexit holds this object until process exit. Tests must call close() themselves.
        atexit.register(self.close)
        build = duckdb.connect(str(self._scratch))
        try:
            for table in ["catalog", "customers", "orders", "campaign_events"]:
                path = str((DATA_DIR / f"{table}.csv").resolve())
                build.execute(
                    f"CREATE TABLE {_ident(table)} AS SELECT * FROM read_csv_auto(?)",
                    [path],
                )
        except BaseException:
            build.close()
            self.close()
            raise
        build.close()
        # reopen read-only; DuckDB refuses read_only on :memory:
        self.conn = duckdb.connect(str(self._scratch), read_only=True)

    def close(self):
        if getattr(self, "_closed", False):
            return
        self._closed = True
        conn = getattr(self, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except duckdb.Error:
                pass
            self.conn = None
        scratch = getattr(self, "_scratch", None)
        if scratch is not None:
            scratch.unlink(missing_ok=True)

    def _query(self, sql, params=None):
        try:
            if params is None:
                return self.conn.execute(sql)
            return self.conn.execute(sql, params)
        except duckdb.Error as e:
            raise WarehouseError(str(e)) from e

    def _catalog_rows(self, where: str, params: list) -> list[DatasetInfo]:
        rows = self._query(
            f"SELECT name, description, owner, tables FROM catalog WHERE {where}", params
        ).fetchall()
        return [DatasetInfo(name=r[0], description=r[1], owner=r[2],
                            tables=[t for t in str(r[3] or "").split(",") if t]) for r in rows]

    async def search_catalog(self, keyword: str) -> list[DatasetInfo]:
        return self._catalog_rows("name ILIKE ? OR description ILIKE ?", [f"%{keyword}%", f"%{keyword}%"])

    async def list_tables(self, dataset: str) -> list[TableInfo]:
        info = self._catalog_rows("name = ?", [dataset])
        tables = []
        for t in info[0].tables if info else []:
            name = _ident(t)
            cols = [r[1] for r in self._query(f"PRAGMA table_info('{name}')").fetchall()]
            tables.append(TableInfo(name=name, columns=cols))
        return tables

    async def dry_run(self, sql: str) -> CostEstimate:
        self._query("EXPLAIN " + sql).fetchall()
        known = [t[0] for t in self._query("SHOW TABLES").fetchall()]
        scanned = 0
        for t in known:
            # word boundary, so "orders" does not match inside "preorders"
            if re.search(rf"\b{re.escape(t)}\b", sql):
                scanned += self._query(f"SELECT count(*) FROM {_ident(t)}").fetchone()[0]
        return CostEstimate(sql=sql, scanned_rows=scanned)

    async def execute(self, sql: str) -> QueryResult:
        cur = self._query(sql)
        rows = [list(r) for r in cur.fetchall()[:10]]
        return QueryResult(columns=[d[0] for d in cur.description], rows=rows)
