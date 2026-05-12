# site_scraper

A guarded web-crawler framework for inspecting webapps, planning safe UI/network extraction workflows, writing DuckDB + Parquet outputs with provenance tracking, and generating FastAPI + Reflex replacement sites from scraped data.

Built on Playwright (browser automation), httpx (HTTP inspection), DuckDB (in-process SQL), PyArrow/Parquet (columnar storage), and Reflex + FastAPI (generated sites). Designed for read-only, human-in-the-loop workflows with strong sanitization and rate-limit defaults.

---

## Prerequisites

| Dependency | Required | Notes |
|-----------|----------|-------|
| [uv](https://docs.astral.sh/uv/) ≥ 0.5 | Yes | Manages the Python environment and entry points |
| Google Chrome or Chromium | Yes | For browser-assisted and authenticated crawling |
| Playwright browser binaries | Yes | Installed separately after `uv sync` |
| Docker + Docker Compose | Optional | For running and validating generated sites |

---

## Quick Start

```bash
# 1. Install all dependencies (including dev and generated-site extras)
uv sync --extra dev --extra generated-site

# 2. Install Playwright browser binaries
uv run python -m playwright install chromium
uv run python -m playwright install-deps chromium

# 3. Create a site config
uv run site-scraper init-site --url "https://example.com" --name example

# 4. Quick HTTP inspection (no browser needed)
uv run site-scraper inspect --site example

# 5. Browser-assisted crawl (requires Chrome on port 9222 — see below)
uv run site-scraper crawl --site example

# 6. Generate a replacement site
uv run site-scraper generate-site --site example

# 7. Start the MCP server for agent use
uv run site-scraper-mcp
```

---

## CLI Command Reference

| Command | Description |
|---------|-------------|
| `site-scraper init-site --url URL --name NAME` | Create site config under `sites/NAME/` |
| `site-scraper auth --site NAME` | Launch Chrome for manual auth, then wait for confirmation |
| `site-scraper launch-browser --url URL --profile PATH` | Start Chrome with remote debugging on port 9222 |
| `site-scraper check-browser --target-domain DOMAIN ...` | Verify Chrome CDP, Playwright, and auth status |
| `site-scraper inspect --site NAME` | HTTP-only quick scan: tables, links, controls |
| `site-scraper crawl --site NAME` | Extract UI tables to Parquet + DuckDB |
| `site-scraper replay-network --site NAME` | Replay captured network requests (placeholder) |
| `site-scraper export --site NAME` | Print paths to the latest run outputs |
| `site-scraper generate-site --site NAME` | Scaffold a FastAPI + Reflex project |
| `site-scraper validate-site --site NAME` | Check generated site file structure |

### Chrome Launch (for authenticated crawling)

```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=secrets/chrome-profile \
  https://example.com

# Then verify connectivity:
uv run site-scraper check-browser \
  --target-domain example.com \
  --url-contains /dashboard \
  --required-text "Dashboard" \
  --signed-out-text "Sign in"
```

---

## MCP Server

The `site-scraper` MCP server exposes all CLI commands as structured tools for use with Claude Code, OpenAI agents, and any MCP-compatible agent framework.

### Starting the Server

```bash
uv run site-scraper-mcp
```

The server communicates over stdio and is started automatically by Claude Code when `.claude/settings.json` registers it.

### Available Tools

| Tool | Description |
|------|-------------|
| `init_site(name, url, auth_required)` | Create a site config |
| `launch_browser(url, port, profile_dir)` | Start Chrome with remote debugging (detached) |
| `check_browser(cdp_url, target_domain, url_contains, ...)` | Preflight CDP + Playwright + auth check |
| `inspect_site(site_name)` | HTTP-only quick scan |
| `crawl_site(site_name, max_pages, max_states)` | Extract UI tables to Parquet + DuckDB |
| `replay_network_requests(site_name, run_id)` | Replay captured network requests |
| `export_run(site_name)` | Return latest run output paths |
| `generate_site(site_name)` | Generate FastAPI + Reflex project |
| `validate_site(site_name)` | Validate generated site file structure |
| `resanitize_run(run_root, site_name)` | Re-run sanitization on all JSON outputs |
| `list_sites()` | List all configured sites |
| `list_runs(site_name)` | List all runs for a site |
| `get_run_artifact(site_name, run_id, artifact)` | Read any JSON artifact from a run |
| `get_completeness_report(site_name, run_id)` | Read the completeness report for a run |

### Claude Code Setup

Claude Code loads MCP servers from a per-user local config (`~/.claude.json`), not from the committed `.claude/settings.json`. After cloning, run this **once** to register the server for your machine:

```bash
claude mcp add --scope local site-scraper -- bash "$(pwd)/.claude/run_mcp.sh"
```

Then start a new Claude Code session — the `mcp__site-scraper__*` tools will be available automatically.

> **Why a wrapper script?** Claude Code does not honor the `cwd` field when spawning MCP servers, so `uv run site-scraper-mcp` fails if invoked from outside the project root. `.claude/run_mcp.sh` resolves the repo root from its own path via `${BASH_SOURCE[0]}`, making it work regardless of where Claude Code starts it.

---

## Claude Code Slash Commands

When working in Claude Code inside this project, these slash commands are available:

| Command | Description |
|---------|-------------|
| `/scrape [url-or-site-name]` | Full workflow: inspect → plan → crawl → generate |
| `/check-browser [domain] [path]` | Preflight browser connectivity verification |
| `/generate [site-name]` | Generate + validate a site from the latest run |
| `/validate [site-name]` | Validate a generated site's file structure |

---

## Workflow Walkthrough

The full workflow follows these steps — the `/scrape` slash command automates all of them:

1. **Create a site config** — `init_site` or `site-scraper init-site`
2. **Launch Chrome** — `launch_browser` tool or manual `google-chrome --remote-debugging-port=9222`
3. **Authenticate** — User logs in manually in Chrome; do not share credentials in chat
4. **Preflight check** — `check_browser` tool verifies CDP, Playwright, and auth status
5. **Quick inspect** — `inspect_site` for tables, links, controls; chrome-devtools MCP for live page
6. **Interaction inventory** — Enumerate all tabs, filters, selectors, pagination, expanders
7. **Network inventory** — Capture XHR/fetch traffic while clicking UI controls
8. **OpenAPI inventory** — Normalize routes, classify endpoints, generate spec and matrix
9. **Per-site plan** — Document targets, guardrails, extraction plan; get user approval
10. **Crawl** — `crawl_site` extracts tables to Parquet + DuckDB; `export_run` shows paths
11. **Design capture** — Screenshots and design signal collection
12. **Generate + validate** — `generate_site` → `validate_site` → `docker compose up --build`

---

## Site Configuration Reference

Site configs are YAML files at `sites/<name>/site.yaml`:

```yaml
name: example
url: https://example.com
auth:
  required: false
  persist_state: false
guardrails:
  allowed_actions:
    - navigate
    - filter
    - sort
    - paginate
    - tab
    - expand
    - scroll
    - download
  blocked_label_patterns:
    - save
    - submit
    - delete
    - remove
    - archive
    - purchase
limits:
  max_pages: 50
  max_states: 200
  max_replay_requests: 200
  max_runtime_seconds: 1800
  concurrency: 2
  delay_ms: 500
rebuild_mode: ask   # ask | clone | redesign | skip
notes: ""
```

---

## Directory Layout

```
site_scraper/
├── sites/<name>/site.yaml          # Site configuration
├── runs/<name>/<run_id>/
│   ├── json/                       # Inspection, events, network, API results
│   ├── parquet/                    # Extracted tables as Parquet files
│   ├── design/                     # Design profile and screenshots
│   ├── openapi/                    # OpenAPI spec, endpoint matrix, probe results
│   └── catalog.duckdb              # DuckDB catalog with views over all parquet
├── generated_sites/<name>/
│   ├── backend/main.py             # FastAPI app serving DuckDB data
│   ├── frontend/app.py             # Reflex frontend
│   ├── data/catalog.duckdb         # Copied DuckDB catalog
│   ├── docker-compose.yml          # Backend (8000) + frontend (3000)
│   └── pyproject.toml              # Generated site's own uv project
├── src/site_scraper/
│   ├── cli.py                      # Typer CLI entry points
│   ├── mcp_server.py               # FastMCP server and tools
│   ├── crawler.py                  # inspect_site, crawl_site, replay_network
│   ├── browser.py                  # Chrome launch helpers
│   ├── generator.py                # Generated site scaffolding
│   ├── storage.py                  # DuckDB + Parquet I/O
│   ├── extractors.py               # HTML table/link/control extraction
│   ├── models.py                   # Pydantic config models
│   └── scripts/browser_connectivity.py  # CDP preflight checks
├── scripts/sites/<name>/           # Site-specific extraction scripts
├── .claude/
│   ├── settings.json               # Permissions and project-scope Claude Code config
│   ├── run_mcp.sh                  # Wrapper that resolves repo root for MCP server launch
│   └── commands/                   # Slash commands: scrape, check-browser, generate, validate
├── .codex/skills/site-scraper/     # Codex/OpenAI agent skill
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/                 # Guardrails, crawl contract, OpenAPI strategy, etc.
├── CLAUDE.md                       # Claude Code project instructions
└── pyproject.toml                  # uv project with all dependencies
```

---

## Safety Defaults

- **Read-only by default** — only navigate, filter, sort, paginate, tab, expand, scroll, download are permitted
- **Mutation block list** — save, submit, delete, remove, archive, purchase, pay, checkout, and similar are blocked by default
- **Human-in-the-loop auth** — no credential prompting, no MFA bypass, no CAPTCHA bypass
- **Output sanitization** — all JSON outputs redact tokens, emails, JWTs, long IDs, and profile fields before saving
- **API scope** — `/auth`, `/user`, `/payment` excluded unless explicitly requested in the approved per-site plan
- **Rate/concurrency limits** — 50 pages, 200 states, 200 requests, 30min runtime, 2 concurrent, 500ms delay (all configurable)
