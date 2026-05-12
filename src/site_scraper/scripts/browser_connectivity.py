from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from playwright.async_api import async_playwright

DEFAULT_CDP = "http://127.0.0.1:9222"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass
class BrowserCheckOptions:
    cdp_url: str = DEFAULT_CDP
    timeout: float = 5.0
    target_domain: str | None = None
    url_contains: str | None = None
    required_text: tuple[str, ...] = ()
    signed_out_text: str | None = None
    signed_in_text: str | None = None
    label: str = "Target visible page"


def print_result(result: CheckResult) -> None:
    prefix = "PASS" if result.ok else "FAIL"
    print(f"{prefix} {result.name}: {result.detail}")


def read_json_version(cdp_url: str, timeout: float) -> tuple[CheckResult, dict[str, Any] | None]:
    url = f"{cdp_url.rstrip('/')}/json/version"
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as error:
        return (
            CheckResult(
                "Chrome debug endpoint",
                False,
                f"could not read {url}: {error}. Launch Chrome with remote debugging.",
            ),
            None,
        )
    browser = payload.get("Browser") or "unknown browser"
    websocket = payload.get("webSocketDebuggerUrl")
    if not websocket:
        return CheckResult("Chrome debug endpoint", False, f"{url} did not expose webSocketDebuggerUrl."), payload
    return CheckResult("Chrome debug endpoint", True, f"{browser} at {url}"), payload


def page_matches(url: str, options: BrowserCheckOptions) -> bool:
    if options.target_domain and options.target_domain not in url:
        return False
    if options.url_contains and options.url_contains not in url:
        return False
    return bool(options.target_domain or options.url_contains)


async def check_playwright_cdp(options: BrowserCheckOptions) -> list[CheckResult]:
    results: list[CheckResult] = []
    timeout_ms = int(options.timeout * 1000)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(options.cdp_url, timeout=timeout_ms)
            results.append(CheckResult("Playwright CDP", True, f"connected to {len(browser.contexts)} browser context(s)."))
            matched_page = None
            all_urls: list[str] = []
            for context in browser.contexts:
                for page in context.pages:
                    all_urls.append(page.url)
                    if page_matches(page.url, options):
                        matched_page = page
                        break
                if matched_page:
                    break
            if matched_page is None:
                detail = "no matching readable tab found"
                if all_urls:
                    detail += f"; open tabs: {', '.join(all_urls[:5])}"
                results.append(CheckResult(options.label, False, detail))
            else:
                title = await matched_page.title()
                body_text = await matched_page.locator("body").inner_text(timeout=timeout_ms)
                missing = [text for text in options.required_text if text and text not in body_text and text not in matched_page.url and text not in title]
                signed_out = bool(options.signed_out_text and options.signed_out_text in body_text)
                signed_in = not options.signed_in_text or options.signed_in_text in body_text
                if signed_out and not signed_in:
                    results.append(CheckResult(options.label, False, "tab is visible but appears signed out. Authenticate in Chrome and keep the target tab open."))
                elif missing:
                    sample = body_text[:180].replace("\n", " ")
                    results.append(CheckResult(options.label, False, f"tab exists but required text is missing: {missing}; sample={sample!r}"))
                else:
                    results.append(CheckResult(options.label, True, f"{title} ({matched_page.url})"))
            await browser.close()
    except Exception as error:
        results.append(CheckResult("Playwright CDP", False, f"connect_over_cdp failed: {error}"))
    return results


async def run_browser_check(options: BrowserCheckOptions) -> list[CheckResult]:
    results: list[CheckResult] = []
    first, _ = read_json_version(options.cdp_url, options.timeout)
    results.append(first)
    if first.ok:
        results.extend(await check_playwright_cdp(options))
    return results


async def async_main(
    cdp_url: str = DEFAULT_CDP,
    target_domain: str | None = None,
    url_contains: str | None = None,
    required_text: list[str] | None = None,
    signed_out_text: str | None = None,
    signed_in_text: str | None = None,
    label: str = "Target visible page",
    timeout: float = 5.0,
) -> int:
    options = BrowserCheckOptions(
        cdp_url=cdp_url,
        timeout=timeout,
        target_domain=target_domain,
        url_contains=url_contains,
        required_text=tuple(required_text or ()),
        signed_out_text=signed_out_text,
        signed_in_text=signed_in_text,
        label=label,
    )
    results = await run_browser_check(options)
    for result in results:
        print_result(result)
    if all(result.ok for result in results):
        return 0
    print(
        "\nRequired before scraping: start Chrome with remote debugging, authenticate when needed, "
        "and keep the target tab open.",
        file=sys.stderr,
    )
    return 1
