from __future__ import annotations

import argparse
import asyncio

from site_scraper.scripts.browser_connectivity import async_main


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic Chrome/CDP preflight before scraping.")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--target-domain", default=None)
    parser.add_argument("--url-contains", default=None)
    parser.add_argument("--required-text", action="append", default=[])
    parser.add_argument("--signed-out-text", default=None)
    parser.add_argument("--signed-in-text", default=None)
    parser.add_argument("--label", default="Target visible page")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--case-number", default=None, help="Compatibility shortcut for MyCasesHub analysis pages.")
    args = parser.parse_args()

    target_domain = args.target_domain
    url_contains = args.url_contains
    required_text = list(args.required_text)
    signed_out_text = args.signed_out_text
    signed_in_text = args.signed_in_text
    label = args.label

    if args.case_number:
        target_domain = target_domain or "mycaseshub.com"
        url_contains = url_contains or args.case_number
        required_text.extend([args.case_number, "Nearby"])
        signed_out_text = signed_out_text or "Sign in"
        signed_in_text = signed_in_text or "My Case"
        label = args.label if args.label != "Target visible page" else "MyCasesHub visible page"

    return asyncio.run(
        async_main(
            cdp_url=args.cdp_url,
            target_domain=target_domain,
            url_contains=url_contains,
            required_text=required_text,
            signed_out_text=signed_out_text,
            signed_in_text=signed_in_text,
            label=label,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
