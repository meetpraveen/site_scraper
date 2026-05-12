# Generated App Contract

Use this reference when generating a FastAPI + Reflex replacement site from scraped data.

## Data Contract

The generated backend must serve real extracted data from DuckDB/Parquet files in the generated project's runtime environment. Avoid DuckDB views that reference absolute source-run paths unless those source files are copied into the generated project and the paths are portable.

Every backend endpoint should declare:

- Source dataset or query.
- Supported filters and sort parameters.
- Pagination behavior.
- Expected row count.
- Empty/error response shape.

## Frontend Contract

Every scraped control represented in the generated UI must be actionable:

- Dropdowns, tabs, buttons, and range controls must update state.
- State changes must call the backend or filter real loaded data.
- Metrics, tables, and charts must update after state changes.
- Disabled controls must explain why they are disabled in the parity report.

Do not use placeholder charts or hard-coded sample rows as if they were scraped data. If a placeholder is unavoidable, visibly label it and list it as incomplete.

## Validation

Run browser validation against the generated site:

- Page loads without console errors that break user flows.
- Representative controls visibly change data.
- Tables paginate or filter correctly.
- Charts render from real data and redraw on selector changes.
- Backend API endpoints return non-empty expected schemas where data exists.
- Docker Compose starts both backend and frontend from a clean environment using declared `uv` dependencies.

## Parity Report

Produce a parity report comparing source and generated site:

- Main sections present or intentionally omitted.
- Controls present, wired, disabled, or omitted.
- Source endpoint counts versus generated endpoint counts.
- Source dataset counts versus generated dataset counts.
- Screenshot observations for layout gaps.
- Remaining work needed before calling the clone complete.
