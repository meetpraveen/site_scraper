# /generate — Generate a Replacement Site

Generate a FastAPI + Reflex replacement site from the latest crawl run for a site.

**Arguments:** `$ARGUMENTS` — site name (e.g. `mycaseshub_msc2390228762`)

---

## Step 1 — Identify the Site

If `$ARGUMENTS` is provided, use it as `site_name`.

If no argument: call `list_sites` and ask the user to choose one.

Confirm the site has at least one crawl run by calling `list_runs(site_name=<name>)`. If no runs exist, tell the user to run `/scrape <site-name>` first.

## Step 2 — Review the Latest Run

Call `get_run_artifact(site_name=<name>, run_id=<latest_run_id>, artifact="inspection")` to review what was extracted.

If a completeness report exists, call `get_completeness_report(site_name=<name>, run_id=<latest_run_id>)` and summarize:
- Tables and row counts extracted
- UI controls covered vs. skipped
- API endpoints scraped

Ask the user: are you happy with this data? Should we regenerate a crawl first?

## Step 3 — Generate the Site

Call `generate_site(site_name=<name>)`.

Report the `generated_path` returned.

## Step 4 — Validate the Structure

Call `validate_site(site_name=<name>)` and display results:

| Check | Status |
|-------|--------|
| site_config | ✓ / ✗ |
| generated_site | ✓ / ✗ |
| compose_file | ✓ / ✗ |
| backend | ✓ / ✗ |
| frontend | ✓ / ✗ |

If any check fails, explain what is missing and how to fix it.

## Step 5 — Container Validation

Instruct the user to run full container validation:

```bash
cd <generated_path>
docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

Acceptance criteria (from `.codex/skills/site-scraper/references/generated-app-contract.md`):
- `/health` returns 200
- `/tables` lists available DuckDB-backed datasets
- Frontend renders without errors and displays data from the backend
- All controls in the frontend trigger visible state changes (no inert/placeholder buttons)
- A parity report compares source screenshots with generated pages

Report any gaps between the scraped data and what the generated site exposes.
