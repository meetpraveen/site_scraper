# /scrape — Full Site Scraping Workflow

You are running the site-scraper workflow for: **$ARGUMENTS**

Read CLAUDE.md for the full skill definition, guardrails, and contracts before proceeding.
Read `.codex/skills/site-scraper/references/guardrails.md` now — do not skip.

---

## Step 1 — Parse Input and Check Existing Sites

Call `list_sites` to see all configured sites.

- If `$ARGUMENTS` looks like a URL (starts with `http`): prepare to call `init_site`.
- If `$ARGUMENTS` looks like a site name: check if it already exists in `list_sites` output.
- If no argument: ask the user for a URL or site name before continuing.

If creating a new site, ask whether authentication is required, then call:
```
init_site(name=<derived-name>, url=<url>, auth_required=<true|false>)
```

## Step 2 — Browser and Authentication Setup

Ask the user: does this site require authentication?

**If auth is required:**
- Offer to launch Chrome via the `launch_browser` MCP tool (detached mode).
- Tell the user: "Please authenticate in the opened browser. Keep the target page open and visible. Reply when ready."
- Wait for the user's confirmation before continuing.

**If no auth:**
- Ask the user to confirm Chrome is running with remote debugging: `google-chrome --remote-debugging-port=9222 <url>`
- Or offer to call `launch_browser` tool to open the URL.

## Step 3 — Preflight Browser Check

Call `check_browser` with:
- `cdp_url`: "http://127.0.0.1:9222" (default)
- `target_domain`: the site's domain
- `url_contains`: a path fragment that identifies the target page
- `signed_in_text` / `signed_out_text`: if auth is required, ask the user for visible indicators

Display results as a table:

| Check | Status | Detail |
|-------|--------|--------|
| Chrome debug endpoint | PASS/FAIL | ... |
| Playwright CDP | PASS/FAIL | ... |
| Target visible page | PASS/FAIL | ... |

**If any check fails: STOP. Explain what the user needs to fix. Do not proceed to inspection.**

Remediation guide:
- Chrome not reachable: launch Chrome with `--remote-debugging-port=9222`
- Playwright failed: run `uv run python -m playwright install chromium`
- Target tab not found: open the target URL in Chrome and keep it in the foreground
- Signed out: authenticate in Chrome and confirm

## Step 4 — Inspect the Site

Call `inspect_site(site_name=<name>)`.

Report the returned structure:
- Number of tables found and their schemas
- Links discovered (summarize by domain/path pattern)
- Controls found (buttons, inputs, selects, tabs — group by type)

Also use `chrome-devtools` MCP tools to:
- Take a screenshot of the current page state
- List network requests captured so far
- Read console messages for any errors
- Take a DOM snapshot to see the full element tree

## Step 5 — Interaction Inventory

Before crawling, build a complete interaction inventory by exploring the live page:

Use `chrome-devtools` MCP to:
1. List all clickable tabs and note their labels
2. Identify all filter controls (selects, checkboxes, date pickers, range sliders)
3. Find pagination controls (next/prev buttons, page numbers, infinite scroll regions)
4. Identify expandable sections, modal triggers, and popover menus
5. Note any route parameters visible in the URL (IDs, slugs, case numbers)
6. Capture dropdown option lists by clicking each select control

For each control, record: label, type, current value, possible values, whether it is safe (read-only) or blocked by guardrails.

**Blocked by default:** save, submit, delete, remove, archive, purchase, pay, checkout, export, download-all, reset-password.

## Step 6 — Network Inventory

Capture API traffic while interacting with UI controls:

Use `chrome-devtools` MCP (`list_network_requests`, `get_network_request`) to:
1. Record all XHR/fetch requests while clicking tabs, filters, selectors, and pagination
2. Note request methods, paths, query parameters, and JSON body fields
3. Identify which requests require authentication (check for Authorization headers)
4. Note response structure (data arrays, counts, pagination metadata)
5. Check local storage and session storage for API keys, cached data, and feature flags

## Step 7 — OpenAPI Inventory

Convert observed network traffic into an API inventory:

1. Normalize route identifiers into path parameters (e.g. `/case/MSC123` → `/case/{caseNumber}`)
2. Collect all unique query parameters and JSON body fields per endpoint
3. Classify each endpoint:
   - `open_or_session_optional` — works without auth
   - `authenticated_or_session_required` — needs a valid session
   - `authenticated_data_api` — returns user-specific data
   - `premium_gated_or_limit_blocked` — requires paid access
   - `out_of_scope_account_api` — /auth, /user, /payment — exclude from primary crawl
4. Describe the endpoint matrix in a markdown table

Read `.codex/skills/site-scraper/references/openapi-api-first.md` for the full extraction protocol.

## Step 8 — Site-Specific Questions

Before producing the plan, ask the user:

1. What is the maximum number of pages to crawl? (default: 50)
2. What is the maximum number of UI states to capture? (default: 200)
3. Are there any controls or routes that should be blocked beyond the defaults?
4. Should the run output be used to generate a replacement site?
5. Visual clone, data-first redesign, or skip site generation?
6. Any rate limit or politeness requirements?

## Step 9 — Per-Site Plan (Required Before Extraction)

Using the answers above, produce a plan using the template in `.codex/skills/site-scraper/references/site-plan-template.md`.

The plan must include:
- Target: URL, site name, auth status
- App structure: pages, routes, main UI sections
- Interaction inventory: every safe and blocked control with status
- Network inventory: endpoint list with auth classification
- Guardrails: confirmed limits and blocked actions
- Extraction plan: what data to extract and in what order
- Validation: how to confirm completeness

**Present the plan to the user. Do not begin extraction until they explicitly approve it.**

## Step 10 — Extract

After plan approval:

1. Call `crawl_site(site_name=<name>, max_pages=<approved>, max_states=<approved>)`
2. Monitor progress. If the crawl surfaces new controls or endpoints not in the plan, pause and report them.
3. After crawl completes, call `export_run(site_name=<name>)` and report the output paths.
4. Optionally call `resanitize_run(run_root=<path>)` to re-run sanitization.

Report the final summary:
- Tables extracted and row counts
- Parquet files written
- DuckDB catalog location
- Any skipped or blocked controls with reasons

## Step 11 — Design and Generation (if requested)

If the user wants a generated site:

1. Take final screenshots via chrome-devtools MCP
2. Ask: clone the visual design, or data-first with new UI?
3. Call `generate_site(site_name=<name>)`
4. Call `validate_site(site_name=<name>)` and report the check results
5. Instruct the user: `cd generated_sites/<name> && docker compose up --build`

Read `.codex/skills/site-scraper/references/generated-app-contract.md` for acceptance criteria.

## Safety Reminder

At every step:
- Read-only operations only. Never click save, submit, delete, purchase, or any mutation control.
- Do not request credentials in chat or store them anywhere.
- Sanitize all outputs — remove tokens, JWTs, emails, long IDs before saving.
- Exclude /auth, /user, /payment endpoints unless the user explicitly requested them in the approved plan.
- If you are unsure whether an action is safe, ask the user before proceeding.
