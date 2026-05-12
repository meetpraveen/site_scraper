from site_scraper.extractors import detect_controls, extract_links, extract_tables


def test_extract_tables():
    html = '<table><thead><tr><th>Name</th><th>Value</th></tr></thead><tbody><tr><td>A</td><td>1</td></tr></tbody></table>'
    tables = extract_tables(html, "https://example.com")
    assert tables[0]["rows"] == [{"Name": "A", "Value": "1", "_source_table_index": 0, "_source_url": "https://example.com"}]


def test_extract_links_absolute():
    assert extract_links('<a href="/x">x</a>', "https://example.com/a") == ["https://example.com/x"]


def test_detect_controls():
    controls = detect_controls('<button>Next</button><select name="range"></select>')
    assert [control["tag"] for control in controls] == ["button", "select"]
