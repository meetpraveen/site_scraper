# /validate — Validate a Generated Site

Check whether a generated site's file structure is complete and report any missing components.

**Arguments:** `$ARGUMENTS` — site name (e.g. `example`)

---

## Step 1 — Identify the Site

If `$ARGUMENTS` is provided, use it as `site_name`.

If no argument: call `list_sites` and ask the user to choose one.

## Step 2 — Run Structural Validation

Call `validate_site(site_name=<name>)`.

Display a check table:

| Check | Status | Notes |
|-------|--------|-------|
| site_config | ✓ PASS / ✗ FAIL | `sites/<name>/site.yaml` |
| generated_site | ✓ PASS / ✗ FAIL | `generated_sites/<name>/` |
| compose_file | ✓ PASS / ✗ FAIL | `generated_sites/<name>/docker-compose.yml` |
| backend | ✓ PASS / ✗ FAIL | `generated_sites/<name>/backend/main.py` |
| frontend | ✓ PASS / ✗ FAIL | `generated_sites/<name>/frontend/app.py` |

## Step 3 — Remediation

**site_config missing:** Run `init_site` or check `sites/<name>/site.yaml` exists.

**generated_site missing:** Run `generate_site` — the project directory was never created.

**compose_file / backend / frontend missing:** The generated project is incomplete. Run `generate_site` again to regenerate the scaffold.

## Step 4 — Container Validation (optional, requires Docker)

For full validation beyond file structure:

```bash
cd generated_sites/<name>
docker compose up --build
```

Then verify:
- `curl http://localhost:8000/health` returns `{"status": "ok"}`
- `curl http://localhost:8000/tables` lists available datasets
- `http://localhost:3000` renders the frontend without errors

For DuckDB data parity, check that table row counts in the API match what was extracted during the crawl run. Read `.codex/skills/site-scraper/references/generated-app-contract.md` for the full acceptance checklist.
