from site_scraper.scripts.browser_connectivity import BrowserCheckOptions, page_matches


def test_page_matches_domain_and_url_fragment():
    options = BrowserCheckOptions(target_domain="example.com", url_contains="/account")
    assert page_matches("https://example.com/account/123", options)
    assert not page_matches("https://example.com/public/123", options)
    assert not page_matches("https://other.test/account/123", options)


def test_page_matches_requires_at_least_one_selector():
    assert not page_matches("https://example.com", BrowserCheckOptions())
