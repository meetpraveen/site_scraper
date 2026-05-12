# AGENTS.md — site_scraper

Agent instructions for working in this repository. Read this before taking any action. This file is authoritative for all AI agents. CLAUDE.md contains Claude Code–specific extensions.

---

## What this project does

`site_scraper` is a **guarded, read-only webapp crawler** that:

1. Inspects web apps via HTTP (`httpx`) and/or authenticated browser sessions (Playwright + Chrome CDP)
2. Extracts UI tables, network traffic, and API schemas into DuckDB + Parquet
3. Optionally scaffolds FastAPI + Reflex replacement sites from the extracted data

It is **not** a general-purpose scraper. Every crawl requires a per-site plan approved by the human operator before extraction begins.

---

## Repository layout

```
site_scraper/
├── src/site_scraper/
│   ├── cli.py            # Typer CLI entry points (site-scraper command)
│   ├── mcp_server.py     # FastMCP server — all 14 MCP tools (async)
│   ├── crawler.py        # inspect_site, crawl_site, replay_network
│   ├── browser.py        # Chrome CDP launch helpers
│   ├── generator.py      # FastAPI + Reflex site scaffolding
│   ├── storage.py        # DuckDB + Parquet I/O
│   ├── extractors.py     # HTML table/link/control extraction
│   ├── models.py         # Pydantic config models
│   └── scripts/
│       └── browser_connectivity.py   # CDP preflight checks
├── sites/<name>/site.yaml            # Site configuration (one per target)
├── runs/<name>/<run_id>/             # Crawl outputs
│   ├── json/                         # Inspection/event/network/API artifacts
│   ├── parquet/                      # Extracted tables
│   ├── design/                       # Screenshots and design profile
│   ├── openapi/                      # OpenAPI spec + endpoint/parameter matrices
│   └── catalog.duckdb                # DuckDB catalog with views over all parquet
├── generated_sites/<name>/           # Scaffolded replacement site
├── .claude/
│   ├── settings.json                 # Claude Code MCP server registration + permissions
│   ├── run_mcp.sh                    # Wrapper: resolves repo root, launches MCP server
│   └── commands/                     # Claude Code slash commands
├── .codex/skills/site-scraper/
│   ├── SKILL.md
│   ├── references/guardrails.md
│   ├── references/site-plan-template.md
│   ├── references/exhaustive-crawl.md
│   ├── references/openapi-api-first.md
│   ├── references/generated-app-contract.md
│   └── references/mycaseshub-lessons.md
├── CLAUDE.md                         # Claude Code project instructions
├── AGENTS.md                         # This file
├── README.md                         # Human-facing docs
└── pyproject.toml                    # uv project + entry points
```

---

## Setup

### Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| `uv` ≥ 0.5 | Yes | Manages the Python environment and entry points |
| Google Chrome or Chromium | Yes | For authenticated and browser-assisted crawling |
| Playwright browser binaries | Yes | Install after `uv sync` |
| Docker + Compose | Optional | For generated-site validation |

### Install

```bash
uv sync --extra dev --extra generated-site
uv run python -m playwright install chromium
uv run python -m playwright install-deps chromium
```

### Register the MCP server (Claude Code, once per machine)

Claude Code reads MCP servers from `~/.claude.json` (per-project, `--scope local`), not from the committed `.claude/settings.json`. Run once after cloning:

```bash
claude mcp add --scope local site-scraper -- bash "$(pwd)/.claude/run_mcp.sh"
```

The wrapper script `run_mcp.sh` resolves the repo root from its own path via `${BASH_SOURCE[0]}`, so it works from any clone regardless of working directory. Claude Code silently ignores the `cwd` field in MCP configs — the wrapper is the correct solution.

---

## MCP server

The server exposes all functionality as structured tools. Start it manually with:

```bash
uv run site-scraper-mcp
```

Communicates over stdio. Started automatically by Claude Code when `.claude/settings.json` is present.

### All 14 MCP tools

| Tool | Signature | Purpose |
|------|-----------|---------|
| `list_sites` | `()` | List all configured sites |
| `list_runs` | `(site_name)` | List all runs for a site |
| `init_site` | `(name, url, auth_required)` | Create site config under `sites/` |
| `launch_browser` | `(url, port?, profile_dir?)` | Start Chrome with remote debugging (detached) |
| `check_browser` | `(cdp_url, target_domain, url_contains?, ...)` | Verify Chrome CDP + Playwright + auth |
| `inspect_site` | `(site_name)` | HTTP-only quick scan: tables, links, controls |
| `crawl_site` | `(site_name, max_pages?, max_states?)` | Extract UI tables to Parquet + DuckDB |
| `replay_network_requests` | `(site_name, run_id?)` | Replay captured network requests |
| `export_run` | `(site_name)` | Return paths for latest run outputs |
| `generate_site` | `(site_name)` | Scaffold FastAPI + Reflex project |
| `validate_site` | `(site_name)` | Check generated site file structure |
| `resanitize_run` | `(run_root, site_name)` | Re-run sanitization on all JSON outputs |
| `get_run_artifact` | `(site_name, run_id, artifact)` | Read any JSON artifact from a run |
| `get_completeness_report` | `(site_name, run_id)` | Read completeness report for a run |

**Important:** `check_browser`, `inspect_site`, `crawl_site`, and `replay_network_requests` are `async def` in `mcp_server.py`. FastMCP runs tools in an async event loop — never use `asyncio.run()` inside these handlers. All internal async calls must use `await`.

---

## CLI reference

```bash
uv run site-scraper init-site --url URL --name NAME
uv run site-scraper inspect --site NAME
uv run site-scraper crawl --site NAME
uv run site-scraper export --site NAME
uv run site-scraper generate-site --site NAME
uv run site-scraper validate-site --site NAME
uv run site-scraper auth --site NAME
uv run site-scraper launch-browser --url URL --profile PATH
uv run site-scraper check-browser --target-domain DOMAIN [options]
uv run site-scraper replay-network --site NAME
```

Prefer MCP tool calls over CLI commands — the tools return structured JSON that is easier to reason over.

---

## Slash commands (Claude Code only)

| Command | Description |
|---------|-------------|
| `/scrape [url-or-site-name]` | Full workflow: inspect → plan → crawl → generate |
| `/check-browser [domain] [path]` | Preflight browser connectivity verification |
| `/generate [site-name]` | Generate + validate a site from latest run |
| `/validate [site-name]` | Validate a generated site's file structure |

Command definitions are in `.claude/commands/*.md`.

---

## Required workflow

Never begin extraction without completing all pre-extraction steps in order.

```
1. Prepare       — uv, Chrome, Playwright, chrome-devtools MCP all available
2. Auth          — launch_browser → user logs in manually → confirm before proceeding
3. Preflight     — check_browser → must pass: CDP, Playwright, target tab, auth state
4. Inspect       — inspect_site + chrome-devtools for live DOM/network/console
5. UI inventory  — every tab/filter/selector/slider/expander/pagination control
6. Network inv.  — XHR/fetch/WS while clicking controls; check JS bundles for API paths
7. OpenAPI inv.  — normalize routes, classify endpoints, build endpoint+parameter matrices
8. Questions     — max pages/states, blocked controls, rate limits, rebuild preference
9. Plan          — produce plan from .codex/skills/site-scraper/references/site-plan-template.md
                   WAIT FOR HUMAN APPROVAL before proceeding
10. Crawl        — crawl_site → export_run → resanitize_run
11. Design       — screenshots; ask: clone, redesign, or skip
12. Generate     — generate_site → validate_site → docker compose up --build
```

---

## Site configuration

`sites/<name>/site.yaml`:

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
    - checkout
    - invite
    - upload
    - send
    - post
    - publish
    - approve
    - reject
    - cancel subscription
    - change password
    - create
    - update
    - edit
    - import
    - sync
    - run job
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

## Safety rules (non-negotiable)

**Read-only by default.** Never automate save, submit, delete, purchase, cancel, upload, send, post, approve, reject, or any control suggesting server-side mutation. When in doubt, skip and document.

**Human-in-the-loop auth only.** Ask the user to authenticate in the browser. Do not request credentials in chat. Do not export cookies, tokens, or auth state. Do not automate CAPTCHA, MFA, or access control bypass.

**Sanitize all outputs before saving.** Redact: bearer/JWT strings, API keys, cookies, CSRF tokens, email addresses, customer IDs, user IDs, profile fields, and long session-like identifiers from all JSON artifacts. Use `resanitize_run` after every crawl.

**API scope.** Exclude `/auth`, `/user`, `/payment` endpoints from primary crawl unless the human explicitly approved them in the per-site plan.

**Stop conditions.** Halt on: repeated errors, logout/session expiry, CAPTCHA, unexpected mutation prompts, account or security warnings, or any action outside the approved plan.

**A premium gate or 403 is a result, not something to work around.** Document it in the completeness report.

---

## Completeness requirements

A crawl is complete only when:

- Every discovered read-only UI control has a crawl status (visited / skipped / blocked) and a reason
- Every safe dropdown/selector/tab has its full option list captured from DOM, accessibility tree, network responses, or JS bundles
- Every safe parameterized endpoint has a parameter matrix with observed values, replayed values, response counts, and blocked/unknown dimensions
- Every table/list/chart dataset has row counts, source endpoint/UI state, and exported Parquet paths
- The completeness report exists and accounts for all gaps

---

## OpenAPI classification

When classifying discovered API endpoints:

| Class | Meaning |
|-------|---------|
| `open_or_session_optional` | Works without auth header |
| `authenticated_or_session_required` | Requires browser session; authless probe fails |
| `authenticated_data_api` | Returns account/case-specific data; session required |
| `premium_gated_or_limit_blocked` | Works partially; paywall or limit for some params |
| `out_of_scope_account_api` | `/auth`, `/user`, `/payment` — excluded from primary crawl |

---

## Generated site contract

If generating a replacement site:

- Backend endpoints must serve real extracted data from DuckDB/Parquet in the generated project's runtime — never hardcoded or fabricated
- All scraped controls in the generated UI must be actionable: clicking/selecting must update state and call backend or filter real data
- DuckDB catalog paths must be portable inside the generated project directory (no absolute source-run paths)
- Docker Compose must start both backend (port 8000) and frontend (port 3000) from a clean environment using declared `uv` dependencies
- Produce a parity report before calling the site complete: sections present/omitted, controls wired/disabled, dataset counts vs source

---

## Key technical patterns

### SSR-first analysis

Some webapps (e.g. MyCasesHub) render all data server-side in the initial HTML. Confirm SSR vs XHR before planning the crawl:

```javascript
// In chrome-devtools evaluate_script, check network requests
// If no XHR/fetch calls carry meaningful data after page load → SSR
// Source of truth is the rendered HTML, not an API
```

When the page is SSR, the crawl target is `GET /page-url` (full HTML), not individual API endpoints. Plan the extraction against the HTML structure, not a network replay loop.

### Vue.js / SPA client-side filters

Controls like dropdowns, tabs, and range sliders in Vue/React apps often filter in-memory without network calls. Confirm by:
1. Opening network panel
2. Clicking the control
3. Checking if any XHR/fetch fires

If no network call: the control is purely client-side. Plan to capture all option states by clicking each option and reading the resulting DOM, not by replaying API requests.

### Range sliders on custom Vue components

Custom drag-based range sliders (not native `<input type="range">`) cannot be moved via `.click()` alone. To interact:
- Use `mousedown` + `mousemove` + `mouseup` events on the drag handle
- Or read the Vue component's reactive state directly via `__vueParentComponent.setupState`
- Or read the JS bundle to understand the navigation target (often purely in-memory, no URL change)

### Chrome remote debugging

Chrome must be launched with `--remote-debugging-port=9222` before `check_browser` or `crawl_site` will work:

```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=secrets/chrome-profile \
  https://target-site.com
```

The `check_browser` preflight verifies: CDP endpoint reachable → Playwright CDP → target tab visible → auth state.

### MCP server async requirement

All tool handlers in `mcp_server.py` that call async functions must be `async def` and use `await`. FastMCP runs tools inside an already-running event loop — calling `asyncio.run()` inside a tool raises:

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

Affected functions: `check_browser`, `inspect_site`, `crawl_site`, `replay_network_requests`.

### MCP server portability

The `.claude/settings.json` registers the MCP server for project-scope Claude Code use, but Claude Code ignores the `cwd` field when spawning MCP processes. The `.claude/run_mcp.sh` wrapper resolves the repo root from `${BASH_SOURCE[0]}`:

```bash
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --project "$REPO_ROOT" site-scraper-mcp "$@"
```

For a new machine, register with:
```bash
claude mcp add --scope local site-scraper -- bash "$(pwd)/.claude/run_mcp.sh"
```

---

## Site-specific notes

### mycaseshub.com

- **Architecture:** Full SSR — all 201 nearby cases and all statistics are rendered server-side in the initial HTML at `/analysis/{caseNumber}`. No XHR/fetch calls carry case analysis data.
- **Primary data target:** `/analysis/MSC2390228762` — parse the SSR HTML
- **Client-side controls:** Summary filter (All Types / I-485 Only), Historical Next Steps year tabs (Overall/2025/2024/2023/2022), Recent Activity filter, Status Distribution buttons, Range slider — all purely in-memory, no network calls
- **Range slider:** Custom drag component. Apply button does NOT navigate to a new URL. It updates `fa.value`/`ba.value` (offset -500 to +500) in Vue reactive state, re-rendering stats in place.
- **Premium-gated:** Cohort toggle, second USCIS combobox — skip, document as premium
- **Out-of-scope APIs:** `/auth/me`, `/user/recent-cases`, `/payment/subscription/me`, `/user/cases`
- **"Want to see other probabilities?"** button — navigates to Dashboard page, not an expander
- **JS bundle location:** `https://mycaseshub.com/assets/Analysis-KZHuAxXc.js` (contains range slider and router logic)

See `.codex/skills/site-scraper/references/mycaseshub-lessons.md` for full lessons from the first rebuild.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `playwright` | Browser automation via Chrome CDP |
| `httpx` | HTTP inspection without browser |
| `duckdb` | In-process SQL over extracted data |
| `pyarrow` / `polars` | Parquet I/O |
| `beautifulsoup4` / `selectolax` / `lxml` | HTML parsing |
| `fastmcp` | MCP server framework (async) |
| `typer` | CLI framework |
| `pydantic` | Config models and validation |
| `tenacity` | Retry logic |
| `rich` | Console output |
| `fastapi` / `reflex` / `uvicorn` | Generated site stack (optional extra) |

Python ≥ 3.11 required. Managed by `uv`.

---

## References

| File | Purpose |
|------|---------|
| `.codex/skills/site-scraper/references/guardrails.md` | Full safety and auth rules |
| `.codex/skills/site-scraper/references/site-plan-template.md` | Required per-site plan format |
| `.codex/skills/site-scraper/references/exhaustive-crawl.md` | UI/API coverage requirements |
| `.codex/skills/site-scraper/references/openapi-api-first.md` | Browser-network OpenAPI extraction |
| `.codex/skills/site-scraper/references/generated-app-contract.md` | Rebuild validation criteria |
| `.codex/skills/site-scraper/references/mycaseshub-lessons.md` | Lessons from first MyCasesHub rebuild |
| `CLAUDE.md` | Claude Code–specific instructions (extends this file) |
| `README.md` | Human-facing documentation and quick-start |
