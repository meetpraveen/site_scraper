---
name: site-scraper
description: Use this skill when the user wants to crawl a public or authenticated website/webapp, discover UI flows, capture network requests, extract data into DuckDB/Parquet, and optionally generate a new Python web app from the scraped data and observed design. Triggers include web scraping, authenticated browser crawling, pagination/filter extraction, network replay, DuckDB/Parquet export, and rebuilding a site from scraped data.
---

# Site Scraper

Use this skill to turn a target website into a planned, guarded extraction workflow and, when requested, a generated FastAPI + Reflex site backed by DuckDB/Parquet data.

Never scrape first. Inspect, ask site-specific questions, produce a per-site plan, then execute only after the user accepts that plan.

For this repository, treat this project-local skill as the canonical `site-scraper` skill. It should include any newer global baseline safeguards plus the stricter project-local crawl and generated-app contracts.

## Prerequisites And Agent Setup

Before executing a site scrape, verify these local capabilities:

- `uv` is available and the project environment can run `uv sync` and `uv run`.
- Chrome or Chromium is installed.
- Chrome DevTools MCP is available to the agent for snapshots, console, network, screenshots, and interaction.
- Playwright is installed in the project environment and browser dependencies are present.
- DuckDB, PyArrow, FastAPI, Reflex, PyYAML, and Playwright are declared in the project `pyproject.toml`.
- Docker and Docker Compose are available when the user asks for containerized validation.

Recommended agent setup sequence:

```bash
cd /<repo_root>/site_scraper
uv sync
uv run python -m playwright install chromium
uv run python -m playwright install-deps chromium
```

For authenticated browser work, the agent should connect to an existing user-authenticated Chrome session or launch one with remote debugging enabled:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/site-scraper-chrome
```

Then use Playwright CDP connection or Chrome DevTools MCP against `http://127.0.0.1:9222`. Do not ask for credentials in chat. Ask the user to authenticate directly in the browser and continue only after they confirm.

Before any authenticated scrape, run the browser connectivity preflight from `/home/praveen/git/site_scraper`:

```bash
uv run site-scraper check-browser --target-domain <domain> --url-contains <path-or-id> --required-text <text>
```

Do not scrape unless it verifies all of these:

- `127.0.0.1:9222/json/version` is reachable.
- Playwright can connect with `connect_over_cdp`.
- The target site tab is visible, readable, and authenticated when authentication is required.

## Packaged Generic Scripts

Reusable scripts must live in package code under `src/site_scraper/scripts/` and be exposed through the `site-scraper` CLI when agents need to run them. Prefer these packaged commands over ad hoc files in the repo root because they travel with the skill/project environment and can be tested generically.

Current generic command:

```bash
uv run site-scraper launch-browser --url https://example.com --profile secrets/example/chrome-profile --port 9222
uv run site-scraper check-browser \
  --target-domain example.com \
  --url-contains /dashboard \
  --required-text "Dashboard" \
  --signed-out-text "Sign in" \
  --signed-in-text "Account"
```

Compatibility wrappers may exist in top-level `scripts/`, but they should delegate to packaged generic code. Do not add new generic automation directly under top-level `scripts/`; add it to `src/site_scraper/scripts/`, expose it in `src/site_scraper/cli.py`, and add tests.

Site-specific scripts belong under `scripts/sites/<site_name>/`. After analyzing a site, an agent may generate site-specific scripts there for selectors, API replay, schema normalization, or generated-app parity. Those scripts may override the generic workflow for that site only, but they must document their provenance in run outputs and keep root-level wrappers thin if backward compatibility is needed.

## MCP Server

When the `site-scraper` MCP server is available, prefer MCP tool calls over direct CLI invocation. The server exposes all CLI commands as structured tools with typed inputs and JSON return values, making them easier to compose in agent workflows.

Start the server:

```bash
uv run site-scraper-mcp
```

MCP tool → CLI equivalents:

| MCP Tool | CLI Equivalent |
|---|---|
| `init_site(name, url, auth_required)` | `site-scraper init-site` |
| `launch_browser(url, port, profile_dir)` | `site-scraper launch-browser` |
| `check_browser(cdp_url, target_domain, ...)` | `site-scraper check-browser` |
| `inspect_site(site_name)` | `site-scraper inspect` |
| `crawl_site(site_name, max_pages, max_states)` | `site-scraper crawl` |
| `replay_network_requests(site_name, run_id)` | `site-scraper replay-network` |
| `export_run(site_name)` | `site-scraper export` |
| `generate_site(site_name)` | `site-scraper generate-site` |
| `validate_site(site_name)` | `site-scraper validate-site` |
| `resanitize_run(run_root, site_name)` | `scripts/sites/<name>/resanitize_run.py` |
| `list_sites()` | _(new — no CLI equivalent)_ |
| `list_runs(site_name)` | _(new — no CLI equivalent)_ |
| `get_run_artifact(site_name, run_id, artifact)` | _(new — no CLI equivalent)_ |
| `get_completeness_report(site_name, run_id)` | _(new — no CLI equivalent)_ |

## Required Workflow

1. Prepare `/home/praveen/git/site_scraper` and use Chrome DevTools MCP for live inspection plus the project CLI for repeatable automation.
2. Open the target URL and determine whether authentication is required. If it is, launch/connect to Chrome on debug port `9222`, ask the user to authenticate manually, and continue after confirmation.
3. For authenticated scraping, call the `check_browser` MCP tool (preferred) or run `uv run site-scraper check-browser ...` as a fallback. Stop unless Chrome debug port, Playwright CDP, and the authenticated target tab all pass.
4. Inspect snapshots, screenshots, console output, controls, tables, routes, and XHR/fetch traffic before scraping.
5. Build an interaction inventory before scraping. Enumerate tabs, selectors, filters, range controls, buttons, expanders, pagination, infinite-scroll regions, route parameters, table controls, chart dropdowns, and any hidden options revealed by menus or popovers.
6. Build a network inventory before scraping. Capture XHR/fetch/WebSocket traffic while using the UI, inspect query/body parameters, review cache keys/local storage/session storage, and search loaded JavaScript bundles for API paths and option constants.
7. Convert the observed network traffic into an API inventory. Generate an OpenAPI YAML/JSON spec, endpoint matrix, parameter matrix, bounded probe results, and auth classification before bulk extraction.
8. Ask site-specific questions for safety and completeness: max depth/pages/states, safe controls, rate limits, login persistence, data priorities, replay boundaries, and rebuild preference.
9. Produce a per-site plan using `references/site-plan-template.md`; do not extract until the user approves it.
10. Extract via API-first crawling plus UI fallback, saving DuckDB-backed Parquet outputs with provenance. For each discovered read-only control/API dimension, record whether it was visited, skipped by guardrail, or blocked by user-approved limits.
11. Capture design signals and ask whether to visually clone, redesign data-first, or skip generated-site work.
12. Generate a child `uv` project with FastAPI, Reflex, Dockerfiles, and Docker Compose, then validate it.

## Exhaustive Crawl Contract

For an app-style page, "complete" means:

- Every discovered read-only UI control has a crawl status and provenance evidence.
- Every selector/dropdown/tab/filter has its option list captured from DOM, accessibility tree, network responses, or app bundles.
- Every safe parameterized API endpoint has a parameter matrix showing observed values, replayed values, response counts, and blocked or unknown dimensions.
- Every table/list/chart dataset has row counts, source endpoint/UI state, and exported DuckDB/Parquet paths.
- Pagination, infinite scroll, date ranges, range sliders, and chart mode selectors are exercised up to the approved limits.
- The generated app implements every scraped control as an actionable state change backed by DuckDB/Parquet or a documented static limitation.
- Placeholder charts, fabricated samples, and inert controls are not acceptable unless they are visibly labeled as placeholders and listed as incomplete in the final report.

Read `references/exhaustive-crawl.md` before executing app-style crawls.

## OpenAPI From Browser Network

For app-style targets with XHR/fetch traffic, create a browser-derived OpenAPI inventory before large crawls:

- Capture network requests while activating tabs, filters, selectors, date ranges, pagination, range sliders, expanders, and chart/table controls.
- Normalize route identifiers into path parameters and collect query parameters plus JSON request body fields.
- Exclude account, auth, user-profile, and payment endpoints from the primary crawl spec unless the user explicitly asks for those datasets.
- Replay only bounded read-only probes first. Compare requests made with the live browser session against requests made without authorization headers.
- Classify endpoints as `open_or_session_optional`, `authenticated_or_session_required`, `authenticated_data_api`, `premium_gated_or_limit_blocked`, or `out_of_scope_account_api`.
- Save `openapi/*.yaml`, `openapi/*.json`, endpoint matrix markdown, parameter matrix parquet, sanitized probe results, and generation summary with no raw headers, cookies, tokens, or credentials.
- Use this API inventory as the primary extraction plan. Use UI scraping only for controls, rendered-only state, visual parity, or API gaps.

Read `references/openapi-api-first.md` before implementing browser-network API extraction.

## Project Commands

Via CLI (always available):

```bash
uv run site-scraper init-site --url "https://example.com" --name example
uv run site-scraper auth --site example
uv run site-scraper launch-browser --url "https://example.com" --profile secrets/example/chrome-profile
uv run site-scraper check-browser --target-domain example.com --url-contains /dashboard --required-text "Dashboard"
uv run site-scraper inspect --site example
uv run site-scraper crawl --site example
uv run site-scraper replay-network --site example
uv run site-scraper export --site example
uv run site-scraper generate-site --site example
uv run site-scraper validate-site --site example
```

Via MCP tools (preferred when the `site-scraper` MCP server is running):

```
init_site(name="example", url="https://example.com")
launch_browser(url="https://example.com", port=9222)
check_browser(target_domain="example.com", url_contains="/dashboard", required_text=["Dashboard"])
inspect_site(site_name="example")
crawl_site(site_name="example", max_pages=50)
export_run(site_name="example")
generate_site(site_name="example")
validate_site(site_name="example")
list_sites()
list_runs(site_name="example")
get_run_artifact(site_name="example", run_id="20260512T015708Z", artifact="inspection")
```

## Safety Defaults

Read-only by default. Do not automate destructive controls, bypass CAPTCHA/MFA/access controls, collect credentials, or persist auth unless explicitly requested per site. Respect authorization boundaries, rate limits, and applicable terms.

Authentication is human-in-the-loop only. The operator may ask the user to log in inside a browser session. Do not request credentials in chat, export cookies/tokens, or persist auth state unless the per-site plan explicitly approves it.

Authenticated scrape outputs must be sanitized before saving. Do not persist request headers. Redact token-like keys, bearer/JWT strings, cookies, CSRF values, email addresses, customer IDs, user IDs, profile fields, and long session-like identifiers. Skip account/payment/user-profile endpoints unless the user explicitly asks for those datasets.

## Generated App Acceptance

The generated app is not done until:

- Backend endpoints serve the extracted datasets from DuckDB/Parquet in the generated project's runtime environment.
- Frontend controls call backend APIs or mutate local state and visibly update tables, charts, metrics, or route state.
- Browser smoke tests verify representative controls, filters, pagination, and chart selectors.
- The site runs through `docker compose` with declared `uv` dependencies, including browser automation dependencies when validation needs Playwright.
- A parity report compares source screenshots/data counts with generated pages and names remaining gaps.

Read `references/generated-app-contract.md` before generating or validating a rebuilt site.

## References

Read `references/guardrails.md` for safety/auth rules, `references/site-plan-template.md` for the required per-site plan format, `references/exhaustive-crawl.md` for UI/API coverage, `references/openapi-api-first.md` for browser-network OpenAPI extraction, and `references/generated-app-contract.md` for rebuild validation.
