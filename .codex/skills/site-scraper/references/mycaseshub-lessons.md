# MyCasesHub Lessons

The first MyCasesHub rebuild exposed issues this project-local skill must prevent:

- A visual clone can look similar while charts, controls, and datasets are materially incomplete.
- Static metric cards and placeholder charts are not a valid replacement for source charts backed by API data.
- Buttons and selectors that do not update data are incomplete, even if their styling matches.
- A nearby-case scrape for one expanded range is not the same as exhaustive coverage across case type, date range, receipt block/monthly modes, chart dropdowns, and pagination.
- Generated DuckDB catalogs must be portable inside the generated child project and Docker image.
- Reflex/FastAPI projects must include all launch files and dependencies needed by `uv` and Docker.
- Authenticated browser captures can expose account routes or identifiers. MyCasesHub-like runs must exclude `/auth`, `/user`, and `/payment` API paths unless explicitly in scope, and must scan outputs for token-like or personal identifiers before validation.

For MyCasesHub-like pages, the plan must explicitly inventory controls in sections such as summary, official processing times, case insights, recent activity, message distribution, case type distribution, cases list, status distribution, case number range analysis, cohort trend over range, and cohort analysis.

Before marking a MyCasesHub-like clone complete, validate that selectors, range controls, expanders, pagination, and chart modes are actionable in the rebuilt app and backed by extracted data.
