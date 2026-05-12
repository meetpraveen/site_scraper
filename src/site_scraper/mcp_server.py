"""MCP server exposing site_scraper CLI commands as structured tools for agents."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from site_scraper.browser import launch_debug_chrome
from site_scraper.cli import latest_run, run_paths
from site_scraper.config import GENERATED_ROOT, RUNS_ROOT, SITES_ROOT, load_site, save_site, site_config_path
from site_scraper.crawler import crawl_site as _crawl_site
from site_scraper.crawler import inspect_site as _inspect_site
from site_scraper.crawler import replay_network
from site_scraper.generator import generate_site as _generate_site
from site_scraper.models import AuthConfig, SiteConfig
from site_scraper.scripts.browser_connectivity import BrowserCheckOptions, run_browser_check

mcp = FastMCP("site-scraper")

# ---------------------------------------------------------------------------
# Generic sanitization helpers used by resanitize_run
# ---------------------------------------------------------------------------

_SECRET_RE = re.compile(
    r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*"
    r"|eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"
    r"|[A-Za-z0-9]{32,}",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_SENSITIVE_PATH_RE = re.compile(r"/(auth|user|payment|profile|account|session|token|login|logout)", re.IGNORECASE)


def _is_sensitive_path(path: str) -> bool:
    return bool(_SENSITIVE_PATH_RE.search(path))


def _sanitize_value(v: Any) -> Any:
    if isinstance(v, str):
        v = _EMAIL_RE.sub("[EMAIL]", v)
        v = _SECRET_RE.sub(lambda m: m.group(0)[:6] + "***", v)
        return v
    return v


def _sanitize_generic(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _sanitize_generic(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_generic(item) for item in data]
    return _sanitize_value(data)


def _filter_sensitive_records(path: Path, data: Any, site_specific_is_sensitive=None) -> Any:
    is_sensitive = site_specific_is_sensitive or _is_sensitive_path
    if path.name not in {"captured_network.json", "safe_api_results.json"}:
        if path.name == "completeness_report.json" and isinstance(data, dict) and isinstance(data.get("apiReplay"), list):
            data["apiReplay"] = [
                row for row in data["apiReplay"]
                if not is_sensitive(str((row or {}).get("endpoint") or ""))
            ]
        return data
    if not isinstance(data, list):
        return data
    return [
        row for row in data
        if not isinstance(row, dict) or not is_sensitive(
            str(row.get("endpoint") or row.get("path") or row.get("url") or "")
        )
    ]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def init_site(name: str, url: str, auth_required: bool = False) -> dict[str, Any]:
    """Create a new site configuration for crawling.

    Creates a YAML config at sites/<name>/site.yaml with default guardrails and limits.
    Call this before running any other tools against a new target site.

    Args:
        name: Short identifier for the site (e.g. "mycaseshub", "example"). Used as directory name.
        url: Full URL of the site to crawl (e.g. "https://example.com/dashboard").
        auth_required: Set True if the site requires login before crawling.

    Returns:
        site_name, config_path (absolute), url
    """
    config = SiteConfig(name=name, url=url, auth=AuthConfig(required=auth_required))
    path = save_site(config)
    return {"site_name": name, "config_path": str(path), "url": url}


@mcp.tool()
def launch_browser(
    url: str,
    port: int = 9222,
    profile_dir: str = "secrets/chrome-profile",
) -> dict[str, Any]:
    """Launch Chrome with remote debugging enabled for browser-assisted crawling.

    Starts Chrome in a detached process. The agent does NOT wait for it to exit.
    The user must authenticate in the opened browser before calling check_browser or inspect_site.

    Args:
        url: URL to open in Chrome.
        port: CDP debug port (default 9222). Change if another Chrome is already on 9222.
        profile_dir: Path to Chrome user-data-dir. Relative paths resolve from the project root.

    Returns:
        pid (Chrome process id), port, url
    """
    process = launch_debug_chrome(url, Path(profile_dir), port=port)
    return {"pid": process.pid, "port": port, "url": url}


@mcp.tool()
async def check_browser(
    cdp_url: str = "http://127.0.0.1:9222",
    target_domain: str | None = None,
    url_contains: str | None = None,
    required_text: list[str] | None = None,
    signed_out_text: str | None = None,
    signed_in_text: str | None = None,
    label: str = "Target visible page",
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Verify Chrome remote-debugging connectivity and authentication status.

    Runs preflight checks: CDP endpoint reachable, Playwright can connect, target tab is
    visible and (when needed) authenticated. Always call this before inspect_site or crawl_site.

    Args:
        cdp_url: Chrome DevTools Protocol URL (default http://127.0.0.1:9222).
        target_domain: Domain that must appear in the target tab URL (e.g. "mycaseshub.com").
        url_contains: Path fragment that must appear in the target tab URL (e.g. "/analysis/MSC").
        required_text: List of strings that must be visible in the page body.
        signed_out_text: Text that, if present, indicates the user is NOT signed in.
        signed_in_text: Text that must be present to confirm sign-in.
        label: Human-readable name for the target page check (used in result messages).
        timeout: Seconds to wait for each check.

    Returns:
        all_passed (bool), checks (list of {name, ok, detail} dicts)
    """
    options = BrowserCheckOptions(
        cdp_url=cdp_url,
        timeout=timeout,
        target_domain=target_domain,
        url_contains=url_contains,
        required_text=tuple(required_text or ()),
        signed_out_text=signed_out_text,
        signed_in_text=signed_in_text,
        label=label,
    )
    results = await run_browser_check(options)
    return {
        "all_passed": all(r.ok for r in results),
        "checks": [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in results],
    }


@mcp.tool()
async def inspect_site(site_name: str) -> dict[str, Any]:
    """Run a quick HTTP inspection of a configured site to discover tables, links, and controls.

    Does NOT require Chrome — uses httpx for a lightweight HTML fetch. Good first step
    to understand page structure before planning a full crawl.

    Args:
        site_name: Site identifier (must match a directory under sites/).

    Returns:
        Inspection results (tables, links, controls) plus run_id and run_root path.

    Raises:
        RuntimeError: If the site config is not found or the HTTP request fails.
    """
    try:
        config = load_site(site_name)
        paths = run_paths(site_name)
        result = await _inspect_site(config, paths)
        result.update({"run_id": paths.run_id, "run_root": str(paths.root)})
        return result
    except FileNotFoundError as e:
        raise RuntimeError(f"Site '{site_name}' not found. Run init_site first. Detail: {e}") from e


@mcp.tool()
async def crawl_site(
    site_name: str,
    max_pages: int | None = None,
    max_states: int | None = None,
) -> dict[str, Any]:
    """Extract UI tables and capture crawl events for a configured site.

    Requires Chrome with CDP running on port 9222 (or whichever port the site config specifies).
    Saves Parquet datasets and DuckDB catalog to runs/<site>/<run_id>/.
    Run check_browser before this to verify connectivity.

    Args:
        site_name: Site identifier.
        max_pages: Override the site config page limit (default 50).
        max_states: Override the site config state limit (default 200).

    Returns:
        Crawl summary dict plus run_id and run_root path.

    Raises:
        RuntimeError: If site config is missing or the crawl fails.
    """
    try:
        config = load_site(site_name)
        if max_pages is not None:
            config.limits.max_pages = max_pages
        if max_states is not None:
            config.limits.max_states = max_states
        paths = run_paths(site_name)
        result = await _crawl_site(config, paths)
        result.update({"run_id": paths.run_id, "run_root": str(paths.root)})
        return result
    except FileNotFoundError as e:
        raise RuntimeError(f"Site '{site_name}' not found. Run init_site first. Detail: {e}") from e


@mcp.tool()
async def replay_network_requests(
    site_name: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Replay captured network requests for a site run (placeholder — not yet implemented).

    Args:
        site_name: Site identifier.
        run_id: Specific run ID to replay. Defaults to a new run timestamp.

    Returns:
        Replay result dict plus run_id and run_root.
    """
    config = load_site(site_name)
    paths = run_paths(site_name, run_id)
    result = await replay_network(config, paths)
    result.update({"run_id": paths.run_id, "run_root": str(paths.root)})
    return result


@mcp.tool()
def export_run(site_name: str) -> dict[str, Any]:
    """Return the file paths for the latest crawl run for a site.

    Use this after crawl_site to discover where Parquet, DuckDB, and JSON outputs landed.

    Args:
        site_name: Site identifier.

    Returns:
        run_root, duckdb (catalog path), parquet_dir path.

    Raises:
        RuntimeError: If no runs exist for the site yet.
    """
    run = latest_run(site_name)
    if run is None:
        raise RuntimeError(f"No runs found for site '{site_name}'. Run crawl_site first.")
    return {
        "run_root": str(run),
        "duckdb": str(run / "catalog.duckdb"),
        "parquet_dir": str(run / "parquet"),
    }


@mcp.tool()
def generate_site(site_name: str) -> dict[str, Any]:
    """Generate a FastAPI + Reflex replacement site from the latest crawl run.

    Creates a child uv project at generated_sites/<site_name>/ with a FastAPI backend
    serving DuckDB/Parquet data, a Reflex frontend, Dockerfiles, and docker-compose.yml.

    Args:
        site_name: Site identifier.

    Returns:
        generated_path (absolute path to the generated project), site_name.

    Raises:
        RuntimeError: If no runs exist for the site or site config is missing.
    """
    try:
        config = load_site(site_name)
        run = latest_run(site_name)
        if run is None:
            raise RuntimeError(f"No runs found for site '{site_name}'. Run crawl_site first.")
        out = _generate_site(config, run)
        return {"generated_path": str(out), "site_name": site_name}
    except FileNotFoundError as e:
        raise RuntimeError(f"Site '{site_name}' not found. Run init_site first. Detail: {e}") from e


@mcp.tool()
def validate_site(site_name: str) -> dict[str, Any]:
    """Validate that a generated site has all required files.

    Checks for: site config, generated project dir, docker-compose.yml, backend/main.py,
    frontend/app.py. Does NOT start Docker — run `docker compose up --build` manually
    for full container validation.

    Args:
        site_name: Site identifier.

    Returns:
        checks dict ({check_name: bool}) and all_passed (bool).
    """
    generated = GENERATED_ROOT / site_name
    checks = {
        "site_config": site_config_path(site_name).exists(),
        "generated_site": generated.exists(),
        "compose_file": (generated / "docker-compose.yml").exists(),
        "backend": (generated / "backend" / "main.py").exists(),
        "frontend": (generated / "frontend" / "app.py").exists(),
    }
    return {"checks": checks, "all_passed": all(checks.values())}


@mcp.tool()
def resanitize_run(run_root: str, site_name: str | None = None) -> dict[str, Any]:
    """Re-run sanitization over all JSON files in a run directory.

    Filters sensitive API endpoints (/auth, /user, /payment, etc.) from
    captured_network.json and safe_api_results.json, and redacts tokens, emails,
    and JWT strings from all JSON files.

    If site_name is "mycaseshub" (or matches a site with a custom sanitizer under
    scripts/sites/<site_name>/), the site-specific sanitizer is used as a supplement.

    Args:
        run_root: Absolute path to the run directory (contains a json/ subdirectory).
        site_name: Optional site name to load a site-specific sanitizer.

    Returns:
        run_root, processed_files (list of modified file paths).

    Raises:
        RuntimeError: If the run directory or its json/ subdirectory does not exist.
    """
    root = Path(run_root)
    json_dir = root / "json"
    if not json_dir.exists():
        raise RuntimeError(f"No json/ subdirectory found in {run_root}. Check the run_root path.")

    # Try to load site-specific sanitizer
    site_sanitize = None
    site_is_sensitive = None
    if site_name:
        site_script_dir = Path(__file__).parent.parent.parent / "scripts" / "sites" / site_name
        if site_script_dir.exists():
            sys.path.insert(0, str(site_script_dir))
            try:
                import importlib
                mod_name = f"extract_{site_name.split('_')[0]}"
                mod = importlib.import_module(mod_name)
                site_sanitize = getattr(mod, "sanitize", None)
                site_is_sensitive = getattr(mod, "is_sensitive_api_path", None)
            except Exception:
                pass
            finally:
                sys.path.pop(0)

    sanitize_fn = site_sanitize or _sanitize_generic
    processed = []
    for path in sorted(json_dir.glob("*.json")):
        data = json.loads(path.read_text())
        data = _filter_sensitive_records(path, data, site_is_sensitive)
        data = sanitize_fn(data)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        processed.append(str(path))

    return {"run_root": run_root, "processed_files": processed}


@mcp.tool()
def list_sites() -> dict[str, Any]:
    """List all configured sites in the sites/ directory.

    Returns:
        sites (list of {name, config_path} dicts).
    """
    if not SITES_ROOT.exists():
        return {"sites": []}
    sites = [
        {"name": d.name, "config_path": str(d / "site.yaml")}
        for d in sorted(SITES_ROOT.iterdir())
        if d.is_dir() and (d / "site.yaml").exists()
    ]
    return {"sites": sites}


@mcp.tool()
def list_runs(site_name: str) -> dict[str, Any]:
    """List all crawl runs for a site, sorted oldest-first.

    Args:
        site_name: Site identifier.

    Returns:
        site_name, runs (list of {run_id, run_root} dicts), latest_run_root.
    """
    root = RUNS_ROOT / site_name
    if not root.exists():
        return {"site_name": site_name, "runs": [], "latest_run_root": None}
    runs = sorted(d for d in root.iterdir() if d.is_dir())
    result = [{"run_id": d.name, "run_root": str(d)} for d in runs]
    return {
        "site_name": site_name,
        "runs": result,
        "latest_run_root": str(runs[-1]) if runs else None,
    }


@mcp.tool()
def get_run_artifact(
    site_name: str,
    run_id: str,
    artifact: str = "inspection",
) -> dict[str, Any]:
    """Read a JSON artifact from a crawl run.

    Common artifacts: inspection, completeness_report, captured_network,
    safe_api_results, interaction_inventory, local_state_sanitized, ui_flow_states,
    api_statistics, crawl_events (jsonl — use get_run_artifact for .json files only).

    Args:
        site_name: Site identifier.
        run_id: Run timestamp directory name (e.g. "20260512T015708Z").
        artifact: Stem of the JSON file under runs/<site>/<run_id>/json/ (without .json).

    Returns:
        Parsed JSON content of the artifact file.

    Raises:
        RuntimeError: If the artifact file does not exist.
    """
    path = RUNS_ROOT / site_name / run_id / "json" / f"{artifact}.json"
    if not path.exists():
        available = [p.stem for p in (path.parent).glob("*.json")] if path.parent.exists() else []
        raise RuntimeError(
            f"Artifact '{artifact}.json' not found in {path.parent}. "
            f"Available: {available or 'none (run does not exist or has no json/ output)'}"
        )
    return json.loads(path.read_text())


@mcp.tool()
def get_completeness_report(site_name: str, run_id: str) -> dict[str, Any]:
    """Read the completeness report for a specific crawl run.

    The completeness report documents which UI controls were visited, skipped by guardrail,
    or blocked; which API endpoints were probed; and which data gaps remain.

    Args:
        site_name: Site identifier.
        run_id: Run timestamp directory name (e.g. "20260512T015708Z").

    Returns:
        Parsed completeness_report.json content.

    Raises:
        RuntimeError: If the report does not exist (only written by full site-specific crawls).
    """
    return get_run_artifact(site_name, run_id, "completeness_report")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
