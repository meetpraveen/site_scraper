from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import httpx

from site_scraper.extractors import detect_controls, extract_links, extract_tables
from site_scraper.models import CrawlEvent, RunPaths, SiteConfig
from site_scraper.storage import ensure_run_dirs, refresh_duckdb_catalog, write_events, write_jsonl, write_parquet_dataset


def hash_state(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


async def inspect_site(config: SiteConfig, paths: RunPaths) -> dict[str, object]:
    ensure_run_dirs(paths)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(str(config.url))
    html = response.text
    result = {
        "url": str(response.url),
        "status_code": response.status_code,
        "final_url": str(response.url),
        "auth_likely_required": _looks_like_login(html, str(response.url)),
        "tables": [{"index": t["index"], "headers": t["headers"], "row_count": len(t["rows"])} for t in extract_tables(html, str(response.url))],
        "links_sample": extract_links(html, str(response.url))[:100],
        "controls": detect_controls(html)[:200],
    }
    (paths.json_root / "inspection.json").write_text(json.dumps(result, indent=2, default=str))
    write_events(paths, [CrawlEvent(url=str(response.url), method="system", state_hash=hash_state(html), event_type="inspect", payload=result)])
    return result


async def crawl_site(config: SiteConfig, paths: RunPaths) -> dict[str, object]:
    ensure_run_dirs(paths)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(str(config.url))
    html = response.text
    all_rows = []
    for table in extract_tables(html, str(response.url)):
        for row in table["rows"]:
            row = dict(row)
            row["_extracted_at"] = datetime.now(timezone.utc).isoformat()
            row["_method"] = "ui-html"
            all_rows.append(row)
    parquet = write_parquet_dataset(paths, "ui_tables", all_rows)
    write_jsonl(paths.json_root / "network_calls.jsonl", [])
    write_events(paths, [CrawlEvent(url=str(response.url), method="ui", state_hash=hash_state(html), event_type="crawl_static", payload={"rows": len(all_rows), "parquet": str(parquet) if parquet else None})])
    refresh_duckdb_catalog(paths)
    return {"rows": len(all_rows), "parquet": str(parquet) if parquet else None, "duckdb": str(paths.duckdb_path)}


async def replay_network(config: SiteConfig, paths: RunPaths) -> dict[str, object]:
    ensure_run_dirs(paths)
    network_file = paths.json_root / "network_calls.jsonl"
    count = sum(1 for line in network_file.read_text().splitlines() if line.strip()) if network_file.exists() else 0
    write_events(paths, [CrawlEvent(url=str(config.url), method="network", state_hash="network", event_type="replay_network_placeholder", payload={"captured_requests": count})])
    refresh_duckdb_catalog(paths)
    return {"captured_requests": count, "status": "network replay scaffold ready"}


def _looks_like_login(html: str, url: str) -> bool:
    lower = f"{url}\n{html[:5000]}".lower()
    return any(needle in lower for needle in ["login", "sign in", "signin", "sso", "password", "multi-factor", "mfa"])
