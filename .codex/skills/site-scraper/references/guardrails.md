# Site Scraper Guardrails

Operate read-only unless the user explicitly approves a broader per-site allowlist. Allowed by default: navigation, filter changes, sorting, pagination, tabs, expanding details, scrolling, and download/export actions that do not mutate server state.

Block controls suggesting save, submit, delete, remove, archive, purchase, checkout, invite, upload, send, post, publish, approve, reject, cancel subscription, change password, create, update, edit, import, sync, or run job unless explicitly allowlisted.

Use human-in-the-loop login. Ask the user to authenticate directly in Chrome. Do not ask for credentials, automate MFA, bypass CAPTCHA, or store cookies/tokens by default.

Every per-site plan must set max pages, max UI states, max replay requests, max runtime, concurrency, and delay/rate limit. Stop on repeated errors, logout, CAPTCHA, unexpected mutation prompts, or account/security warnings.

Replay only safe read-only requests. Prefer GET. For POST-backed search APIs, replay only after confirming the endpoint is query-only. Never export auth tokens into reports.
