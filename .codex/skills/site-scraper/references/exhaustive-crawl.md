# Exhaustive App Crawl Requirements

Use this reference for app-style pages with filters, charts, tables, tabs, pagination, range sliders, or authenticated API traffic.

## Discovery

Create two inventories before extraction:

- UI inventory: routes, tabs, dropdowns, segmented controls, sliders, date pickers, table controls, pagination, infinite scroll, accordions, menus, modal launchers, chart controls, and export/download controls.
- Network inventory: XHR/fetch/WebSocket endpoints, request method, query parameters, JSON body schema, response shape, cache keys, local/session storage, and API paths found in loaded JavaScript bundles.

For each control, record its label, DOM selector or accessibility path, current value, possible values, source of possible values, safety classification, and owner section.

## Enumeration

For each safe read-only control:

- Visit every listed option when the option count is within approved limits.
- For range controls, record min, max, current value, step, and approved sampling strategy.
- For date controls, capture available presets and explicit date min/max where exposed.
- For pagination, collect all pages or the approved maximum, including cursor/offset parameters.
- For infinite scroll, scroll until exhaustion or the approved item/page limit.
- For chart modes, switch every mode and capture the backing data response.

When the cartesian product is too large, propose a bounded matrix before scraping. Do not silently sample broad combinations.

## Network Replay

Replay only safe read-only requests. Prefer GET. POST requests may be replayed only when the endpoint is query-only and the plan documents why it is safe.

For every replayed endpoint, store:

- Request method and URL path.
- Redacted query/body parameters.
- UI state that produced the request.
- Response status, count, schema hash, and output dataset.
- Retry/error status.

Do not export cookies, bearer tokens, CSRF tokens, or other secrets into reports. Do not persist request headers. Redact token-like keys, bearer/JWT strings, cookies, CSRF values, email addresses, customer IDs, user IDs, profile fields, and long session-like identifiers. Skip account/payment/user-profile endpoints unless explicitly in scope.

## Completeness Report

Every crawl run must write a completeness report with:

- Controls discovered, visited, skipped, and blocked.
- Endpoints discovered, replayed, skipped, and blocked.
- Dataset row counts and exported files.
- Parameter dimensions covered.
- Gaps caused by auth, limits, errors, paywalls, CAPTCHA, ambiguous mutation risk, or user-approved bounds.

A run with unvisited safe controls or unreplayed safe endpoints is incomplete unless the report explains the approved limit or blocker.
