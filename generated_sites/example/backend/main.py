from pathlib import Path

import duckdb
from fastapi import FastAPI

app = FastAPI(title="Generated scraped-data API")
DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
DUCKDB_PATH = DATA_ROOT / "catalog.duckdb"

@app.get("/health")
def health():
    return {"ok": True, "duckdb_exists": DUCKDB_PATH.exists()}

@app.get("/tables")
def tables():
    if not DUCKDB_PATH.exists():
        return []
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        rows = con.execute("select table_name from information_schema.tables where table_schema = 'scraped'").fetchall()
        return [row[0] for row in rows]
    finally:
        con.close()
