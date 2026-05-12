from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from site_scraper.models import CrawlEvent, RunPaths


def ensure_run_dirs(paths: RunPaths) -> None:
    for path in [paths.root, paths.parquet_root, paths.json_root, paths.screenshot_root, paths.design_root]:
        path.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")


def write_events(paths: RunPaths, events: list[CrawlEvent]) -> None:
    write_jsonl(paths.json_root / "crawl_events.jsonl", [event.model_dump(mode="json") for event in events])


def write_parquet_dataset(paths: RunPaths, dataset: str, rows: list[dict[str, Any]]) -> Path | None:
    if not rows:
        return None
    out = paths.parquet_root / f"{dataset}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), out)
    return out


def refresh_duckdb_catalog(paths: RunPaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(paths.duckdb_path))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS scraped")
        for parquet in paths.parquet_root.glob("*.parquet"):
            table_name = parquet.stem.replace("-", "_")
            con.execute(f"CREATE OR REPLACE VIEW scraped.{table_name} AS SELECT * FROM read_parquet(?)", [str(parquet)])
    finally:
        con.close()
