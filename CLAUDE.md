# site_scraper — Claude Code Project

`site_scraper` is a guarded web-crawler framework that inspects webapps, plans safe UI/network extraction workflows, writes DuckDB + Parquet outputs with provenance tracking, and generates FastAPI + Reflex replacement sites from scraped data.

## MCP Server

This project registers the **`site-scraper`** MCP server via `.claude/settings.json`. Always prefer MCP tool calls over `uv run site-scraper ...` shell commands — the tools return structured JSON that is easier for you to reason over.

The server starts automatically when Claude Code opens this project. To start it manually:

```bash
uv run site-scraper-mcp
```

### Available Tools

| Tool | Purpose |
|------|---------|
| `init_site(name, url, auth_required)` | Create a site config under `sites/` |
| `launch_browser(url, port, profile_dir)` | Start Chrome with remote debugging (detached) |
| `check_browser(cdp_url, target_domain, ...)` | Verify Chrome CDP, Playwright, auth status |
| `inspect_site(site_name)` | HTTP-only quick scan: tables, links, controls |
| `crawl_site(site_name, max_pages, max_states)` | Extract UI tables to Parquet + DuckDB |
| `replay_network_requests(site_name, run_id)` | Replay captured network requests |
| `export_run(site_name)` | Return paths for the latest run outputs |
| `generate_site(site_name)` | Scaffold a FastAPI + Reflex project from latest run |
| `validate_site(site_name)` | Check generated site file structure |
| `resanitize_run(run_root, site_name)` | Re-run sanitization on all JSON outputs |
| `list_sites()` | List all configured sites |
| `list_runs(site_name)` | List all runs for a site |
| `get_run_artifact(site_name, run_id, artifact)` | Read any JSON artifact from a run |
| `get_completeness_report(site_name, run_id)` | Read completeness report for a run |

## Slash Commands

| Command | Description |
|---------|-------------|
| `/scrape [url-or-site-name]` | Full inspection → plan → crawl → generate workflow |
| `/check-browser [domain] [path]` | Preflight browser connectivity check |
| `/generate [site-name]` | Generate + validate a site from the latest run |
| `/validate [site-name]` | Validate a generated site's file structure |

## Prerequisites

```bash
uv sync --extra dev --extra generated-site
uv run python -m playwright install chromium
uv run python -m playwright install-deps chromium
# Docker (optional, for generated-site validation)
```

For authenticated browser work, connect to an existing user-authenticated Chrome session or launch one:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=secrets/chrome-profile <url>
```

Do not ask for credentials in chat. Ask the user to authenticate directly in the browser.

## Required Workflow

Never scrape first. Follow this sequence:

1. **Prepare** — Open the project in the working directory. Confirm `uv`, Chrome, Playwright, and chrome-devtools MCP are all available.

2. **Determine auth** — Open the target URL. Decide whether authentication is required. If so, use `launch_browser` MCP tool or instruct the user to start Chrome with `--remote-debugging-port=9222`, then ask them to authenticate manually and confirm before proceeding.

3. **Preflight check** — Call `check_browser` MCP tool. Stop and report if any check fails — do not proceed until Chrome CDP, Playwright, and the authenticated target tab all pass.

4. **Inspect** — Call `inspect_site`. Also use chrome-devtools MCP for live snapshots, screenshots, console output, and network inspection. Review discovered controls, tables, links, and routes.

5. **Interaction inventory** — Before crawling, enumerate every tab, selector, filter, range control, button, expander, pagination element, route parameter, table control, chart dropdown, and hidden option revealed by menus or popovers.

6. **Network inventory** — Capture XHR/fetch/WebSocket traffic while using the UI. Inspect query/body parameters, cache keys, local storage, and session storage. Search loaded JavaScript bundles for API paths and option constants.

7. **OpenAPI inventory** — Convert observed network traffic into an API inventory. Generate an OpenAPI YAML/JSON spec, endpoint matrix, parameter matrix, bounded probe results, and auth classification. Exclude account/auth/payment endpoints unless the user explicitly asks for them.

8. **Site-specific questions** — Ask about max depth/pages/states, safe controls, rate limits, login persistence, data priorities, replay boundaries, and rebuild preference.

9. **Per-site plan** — Produce a plan using `.codex/skills/site-scraper/references/site-plan-template.md`. Do not extract until the user approves it.

10. **Extract** — After approval, call `crawl_site`. For each discovered read-only control/API dimension, record whether it was visited, skipped by guardrail, or blocked by approved limits. Then call `export_run`.

11. **Design signals** — Capture screenshots and ask whether to visually clone, redesign data-first, or skip generated-site work.

12. **Generate and validate** — Call `generate_site` then `validate_site`. Instruct the user to run `docker compose up --build` for container validation.

## Safety Defaults

Read-only by default. Do not automate destructive controls, bypass CAPTCHA/MFA/access controls, collect credentials, or persist auth unless explicitly requested per site. Respect authorization boundaries, rate limits, and applicable terms.

Authentication is human-in-the-loop only. The operator may ask the user to log in inside a browser session. Do not request credentials in chat, export cookies/tokens, or persist auth state unless the per-site plan explicitly approves it.

Authenticated scrape outputs must be sanitized before saving. Do not persist request headers. Redact token-like keys, bearer/JWT strings, cookies, CSRF values, email addresses, customer IDs, user IDs, profile fields, and long session-like identifiers. Skip account/payment/user-profile endpoints unless the user explicitly asks for those datasets.

## Exhaustive Crawl Contract

For an app-style page, "complete" means:

- Every discovered read-only UI control has a crawl status and provenance evidence.
- Every selector/dropdown/tab/filter has its option list captured from DOM, accessibility tree, network responses, or app bundles.
- Every safe parameterized API endpoint has a parameter matrix showing observed values, replayed values, response counts, and blocked or unknown dimensions.
- Every table/list/chart dataset has row counts, source endpoint/UI state, and exported DuckDB/Parquet paths.
- Pagination, infinite scroll, date ranges, range sliders, and chart mode selectors are exercised up to the approved limits.
- The generated app implements every scraped control as an actionable state change backed by DuckDB/Parquet or a documented static limitation.
- Placeholder charts, fabricated samples, and inert controls are not acceptable unless they are visibly labeled as placeholders and listed as incomplete in the final report.

Read `.codex/skills/site-scraper/references/exhaustive-crawl.md` before executing app-style crawls.

## Generated App Acceptance

The generated app is not done until:

- Backend endpoints serve the extracted datasets from DuckDB/Parquet in the generated project's runtime environment.
- Frontend controls call backend APIs or mutate local state and visibly update tables, charts, metrics, or route state.
- Browser smoke tests verify representative controls, filters, pagination, and chart selectors.
- The site runs through `docker compose` with declared `uv` dependencies, including browser automation dependencies when validation needs Playwright.
- A parity report compares source screenshots/data counts with generated pages and names remaining gaps.

Read `.codex/skills/site-scraper/references/generated-app-contract.md` before generating or validating a rebuilt site.

## References

- `.codex/skills/site-scraper/references/guardrails.md` — full safety and auth rules
- `.codex/skills/site-scraper/references/site-plan-template.md` — required per-site plan format
- `.codex/skills/site-scraper/references/exhaustive-crawl.md` — UI/API coverage requirements
- `.codex/skills/site-scraper/references/openapi-api-first.md` — browser-network OpenAPI extraction
- `.codex/skills/site-scraper/references/generated-app-contract.md` — rebuild validation criteria
- `.codex/skills/site-scraper/references/mycaseshub-lessons.md` — lessons from the first full rebuild
