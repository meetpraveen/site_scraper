# /check-browser — Browser Connectivity Preflight

Run a preflight check to verify Chrome remote debugging is active, Playwright can connect, and the target tab is visible and authenticated.

**Arguments:** `$ARGUMENTS` — parse as `[domain] [path-fragment]`, e.g. `mycaseshub.com /analysis/MSC`

---

## Step 1 — Parse Arguments

Extract from `$ARGUMENTS`:
- `target_domain`: the hostname (e.g. "mycaseshub.com")
- `url_contains`: a path fragment that identifies the correct tab (e.g. "/analysis/MSC")

If no arguments are provided, ask the user:
1. What is the target domain?
2. Is there a URL path fragment or page title that identifies the correct tab?
3. Is authentication required? If so, what text appears when signed in / signed out?

## Step 2 — Run the Check

Call `check_browser` with the parsed parameters. Example:

```
check_browser(
  cdp_url="http://127.0.0.1:9222",
  target_domain=<domain>,
  url_contains=<path-fragment>,
  signed_in_text=<text-if-known>,
  signed_out_text=<text-if-known>,
  timeout=5.0
)
```

## Step 3 — Report Results

Display a clear pass/fail table:

| Check | Status | Detail |
|-------|--------|--------|
| Chrome debug endpoint | ✓ PASS / ✗ FAIL | Version string or error |
| Playwright CDP | ✓ PASS / ✗ FAIL | Contexts connected or error |
| Target visible page | ✓ PASS / ✗ FAIL | Page title + URL or reason |

If `all_passed` is true: confirm the user can proceed with `/scrape` or `crawl_site`.

## Step 4 — Remediation (if any check fails)

**Chrome debug endpoint FAIL:**
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=secrets/chrome-profile <url>
# or use launch_browser MCP tool
```

**Playwright CDP FAIL:**
```bash
uv run python -m playwright install chromium
uv run python -m playwright install-deps chromium
```

**Target tab not found:**
- Open `<url>` in the Chrome window connected to port 9222
- Keep the tab visible and in the foreground
- Do not open DevTools over the target page

**Signed out:**
- Authenticate in Chrome manually
- Do not share credentials in chat
- Re-run `/check-browser` after authenticating to confirm

Do not proceed with any crawl operation until all checks pass.
