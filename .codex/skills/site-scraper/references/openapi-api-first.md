# OpenAPI API-First Extraction

Use this reference when a target webapp exposes XHR, fetch, or WebSocket traffic that can be turned into a repeatable data crawl.

## Required Outputs

- `openapi/<site>.openapi.yaml`
- `openapi/<site>.openapi.json`
- `openapi/endpoint_matrix.md`
- `openapi/parameter_matrix.parquet`
- `openapi/probe_results.json`
- `openapi/authless_probe_results.json`
- `openapi/generation_summary.json`

All saved outputs must be sanitized. Do not save request headers, cookies, bearer tokens, CSRF values, refresh tokens, auth state, profile records, payment data, or account-management responses.

## Discovery

1. Start from the browser session the user can authenticate in.
2. Activate visible controls and inspect the network panel for the API origin.
3. Record every read-only route, method, status code, query parameter, JSON request body field, and response shape.
4. Search loaded JavaScript bundles for additional endpoint paths and option constants.
5. Normalize IDs in URLs into path parameters, such as `/case/{caseNumber}`.
6. Keep account, auth, user-profile, and payment APIs outside the primary crawl spec unless the user explicitly asks for them.

## Bounded Probing

Run small read-only probes before bulk extraction:

- Replay observed GETs with one or two small parameter values.
- For POST endpoints, replay only known read-only lookup bodies.
- Probe large range controls with low limits first.
- Compare live browser session requests with requests made without authorization headers.
- Record 401, 403, paywall, CORS/fetch failures, empty responses, and rate-limit responses as crawl constraints.

Do not bypass CAPTCHA, MFA, premium gates, paywalls, or authorization boundaries. A 403 or premium response is a result, not a failure to work around.

## Classification

Classify each operation:

- `open_or_session_optional`: bounded probe works without an authorization header.
- `authenticated_or_session_required`: works with the browser session but authless probing fails or is rejected.
- `authenticated_data_api`: known case/account-specific data API that should run only inside the approved authenticated session.
- `premium_gated_or_limit_blocked`: returns useful data for some ranges but 403/paywall/limit responses for others.
- `out_of_scope_account_api`: account, auth, user-profile, or payment route excluded from data crawling.

## Extraction Plan

Use the generated OpenAPI inventory as the primary crawler contract:

- Build crawl loops from `parameter_matrix.parquet`.
- Expand option sets from API responses, DOM selectors, and loaded app constants.
- Store raw sanitized API responses plus normalized tables in DuckDB-backed Parquet.
- Preserve provenance columns: endpoint, method, parameter values, status code, fetched_at, source run, and auth category.
- Use UI crawling as fallback for rendered-only content, hidden controls, charts without API parity, and visual validation.

## Validation

Before calling the crawl complete:

- The OpenAPI YAML parses cleanly.
- Endpoint and parameter matrices list all observed filters/selectors/ranges.
- Authless and authenticated probe results are present.
- Sensitive scans show no raw tokens, cookies, profile payloads, or account/payment endpoints.
- Bulk extraction limits match the approved per-site plan.
