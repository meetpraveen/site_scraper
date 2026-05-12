from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def extract_tables(html: str, base_url: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "lxml")
    tables: list[dict[str, object]] = []
    for index, table in enumerate(soup.find_all("table")):
        headers = [cell.get_text(" ", strip=True) for cell in table.select("thead th")]
        rows = []
        for tr in table.select("tbody tr") or table.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            if not cells or cells == headers:
                continue
            row = dict(zip(headers, cells, strict=True)) if headers and len(headers) == len(cells) else {f"col_{i + 1}": value for i, value in enumerate(cells)}
            row["_source_table_index"] = index
            row["_source_url"] = base_url
            rows.append(row)
        tables.append({"index": index, "headers": headers, "rows": rows})
    return tables


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    return sorted({urljoin(base_url, a.get("href")) for a in soup.find_all("a", href=True) if a.get("href")})


def detect_controls(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    controls = []
    for element in soup.select("button, input, select, textarea, [role=button], [role=tab]"):
        label = element.get("aria-label") or element.get("name") or element.get_text(" ", strip=True)
        controls.append({"tag": element.name or "unknown", "type": element.get("type", ""), "label": label.strip(), "id": element.get("id", ""), "name": element.get("name", "")})
    return controls
