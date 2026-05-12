from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from site_scraper.browser import launch_debug_chrome, wait_for_user_auth
from site_scraper.config import GENERATED_ROOT, RUNS_ROOT, load_site, save_site, site_config_path
from site_scraper.crawler import crawl_site, inspect_site, replay_network
from site_scraper.generator import generate_site as generate_site_project
from site_scraper.models import AuthConfig, RunPaths, SiteConfig
from site_scraper.scripts.browser_connectivity import async_main as browser_check_main

app = typer.Typer(no_args_is_help=True)
console = Console()


def run_paths(site: str, run_id: str | None = None) -> RunPaths:
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return RunPaths(site=site, run_id=run_id, root=RUNS_ROOT / site / run_id)


def latest_run(site: str) -> Path | None:
    root = RUNS_ROOT / site
    if not root.exists():
        return None
    runs = sorted(path for path in root.iterdir() if path.is_dir())
    return runs[-1] if runs else None


@app.command("init-site")
def init_site(
    url: str = typer.Option(..., "--url"),
    name: str = typer.Option(..., "--name"),
    auth_required: bool = False,
) -> None:
    path = save_site(SiteConfig(name=name, url=url, auth=AuthConfig(required=auth_required)))
    console.print(f"Created site config: {path}")


@app.command("auth")
def auth(site: str = typer.Option(..., "--site"), port: int = 9222) -> None:
    config = load_site(site)
    profile = Path("secrets") / site / "chrome-profile"
    launch_debug_chrome(str(config.url), profile, port=port)
    asyncio.run(wait_for_user_auth())
    console.print("Authentication step complete. Continue with inspect/crawl in the same browser session when using MCP.")


@app.command("launch-browser")
def launch_browser(
    url: str = typer.Option(..., "--url"),
    profile: Path = typer.Option(Path("secrets") / "chrome-profile", "--profile"),
    port: int = typer.Option(9222, "--port"),
    detach: bool = typer.Option(False, "--detach"),
) -> None:
    process = launch_debug_chrome(url, profile, port=port)
    console.print(f"Chrome launched on debug port {port}.")
    if detach:
        console.print("Detached Chrome process; verify it stays running before scraping.")
        return
    console.print("Keep this command running while scraping. Press Ctrl+C to stop Chrome.")
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()


@app.command("check-browser")
def check_browser(
    cdp_url: str = typer.Option("http://127.0.0.1:9222", "--cdp-url"),
    target_domain: str | None = typer.Option(None, "--target-domain"),
    url_contains: str | None = typer.Option(None, "--url-contains"),
    required_text: list[str] | None = typer.Option(None, "--required-text"),
    signed_out_text: str | None = typer.Option(None, "--signed-out-text"),
    signed_in_text: str | None = typer.Option(None, "--signed-in-text"),
    label: str = typer.Option("Target visible page", "--label"),
    timeout: float = typer.Option(5.0, "--timeout"),
) -> None:
    code = asyncio.run(
        browser_check_main(
            cdp_url=cdp_url,
            target_domain=target_domain,
            url_contains=url_contains,
            required_text=required_text,
            signed_out_text=signed_out_text,
            signed_in_text=signed_in_text,
            label=label,
            timeout=timeout,
        )
    )
    if code:
        raise typer.Exit(code)


@app.command("inspect")
def inspect(site: str = typer.Option(..., "--site")) -> None:
    config = load_site(site)
    paths = run_paths(site)
    result = asyncio.run(inspect_site(config, paths))
    console.print_json(json.dumps(result, default=str))
    console.print(f"Inspection output: {paths.root}")


@app.command("crawl")
def crawl(site: str = typer.Option(..., "--site")) -> None:
    config = load_site(site)
    paths = run_paths(site)
    result = asyncio.run(crawl_site(config, paths))
    console.print_json(json.dumps(result, default=str))
    console.print(f"Crawl output: {paths.root}")


@app.command("replay-network")
def replay(site: str = typer.Option(..., "--site"), run_id: str | None = None) -> None:
    config = load_site(site)
    paths = run_paths(site, run_id) if run_id else run_paths(site)
    result = asyncio.run(replay_network(config, paths))
    console.print_json(json.dumps(result, default=str))


@app.command("export")
def export(site: str = typer.Option(..., "--site")) -> None:
    run = latest_run(site)
    if run is None:
        raise typer.BadParameter(f"No runs found for site {site}")
    console.print(f"Latest run: {run}")
    console.print(f"DuckDB: {run / 'catalog.duckdb'}")
    console.print(f"Parquet: {run / 'parquet'}")


@app.command("generate-site")
def generate_site(site: str = typer.Option(..., "--site")) -> None:
    config = load_site(site)
    out = generate_site_project(config, latest_run(site))
    console.print(f"Generated site: {out}")


@app.command("validate-site")
def validate_site(site: str = typer.Option(..., "--site")) -> None:
    generated = GENERATED_ROOT / site
    checks = {
        "site_config": site_config_path(site).exists(),
        "generated_site": generated.exists(),
        "compose_file": (generated / "docker-compose.yml").exists(),
        "backend": (generated / "backend" / "main.py").exists(),
        "frontend": (generated / "frontend" / "app.py").exists(),
    }
    console.print_json(json.dumps(checks))
    if not all(checks.values()):
        raise typer.Exit(1)
