"""
Trending-products lookup for Beacon AI's Sub-Trend Drill-Down.

Deterministic, no LLM call: parses the curated Top-20 trending-product markdown
reports already checked into data/raw/reports/ (repo root, outside
india-trend-radar/) instead of asking a model to invent a list. Two report
formats exist in that folder today and both are handled:

  - a single pipe-delimited "## Top 20 Table" section
    (US_Top20_Trending_Products_2026.md, China_Top20_Trending_Products_2025.md,
    China_Top20_Trending_Products_2026.md)
  - a categorized numbered-list format under "## Top 20 Trending Products by
    Category" (US-2025-Top20-Trending-Products-Report.md)

Table columns differ between files (the US table has 6 columns incl. price
band; the China tables have 4), so the table parser only relies on column 1
(rank) and column 2 (product name) and folds the rest into one free-text
"signal_and_source" field rather than mapping specific column names.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_REPORT_DIR = REPO_ROOT_DIR / "data" / "raw" / "reports"

# Filenames in data/raw/reports/ are not consistently formatted (e.g.
# "US_Top20_Trending_Products_2026.md" vs "US-2025-Top20-Trending-Products-Report.md"),
# so files are matched by pattern rather than exact name.
REGION_FILENAME_PATTERNS = {
    "United States": re.compile(r"^us[-_].*top.?20.*trending.*products", re.IGNORECASE),
    "China": re.compile(r"^china[-_].*top.?20.*trending.*products", re.IGNORECASE),
}

YEAR_PATTERN = re.compile(r"(20\d{2})")
_LIST_ITEM_RE = re.compile(r"^\*\*(\d+)\.\s+(.+?)\*\*\s*$")
_CATEGORY_HEADING_RE = re.compile(r"^###\s+(.+?)\s*\(\d+\)\s*$")
_MARKDOWN_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _strip_markdown_emphasis(text: str) -> str:
    """Source reports use **bold** to call out headline stats inline (e.g. "**+7,043%
    YoY**"). That's meant for markdown rendering, but signal_and_source is displayed as
    plain text (st.dataframe's TextColumn doesn't render markdown), so left alone the
    literal "**" markers show up in the UI. Strip them, keeping the wrapped text."""
    return _MARKDOWN_BOLD_RE.sub(r"\1", text).replace("**", "")


def _discover_report_files(region: str, report_dir: Path | None = None) -> list[Path]:
    pattern = REGION_FILENAME_PATTERNS.get(region)
    root = report_dir or DEFAULT_REPORT_DIR
    if not pattern or not root.exists():
        return []
    return sorted(path for path in root.glob("*.md") if pattern.search(path.name))


def _extract_year(path: Path, text: str) -> int:
    name_matches = YEAR_PATTERN.findall(path.name)
    if name_matches:
        return int(name_matches[-1])
    text_match = YEAR_PATTERN.search(text[:500])
    return int(text_match.group(1)) if text_match else 0


def _section(text: str, heading: str) -> str | None:
    """Body of the first `## {heading}` section, up to the next `## ` heading."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}.*?$(.*?)(?=^##\s|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def _parse_table_format(text: str) -> list[dict]:
    body = _section(text, "Top 20 Table")
    if not body:
        return []
    rows: list[dict] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not re.match(r"^\d+$", cells[0]):
            continue  # header row, separator row ("---"), or blank
        product = cells[1] if len(cells) > 1 else ""
        if not product:
            continue
        detail = _strip_markdown_emphasis(" | ".join(c for c in cells[2:] if c))
        rows.append(
            dict(rank=int(cells[0]), product=product, category=None, signal_and_source=detail)
        )
    return rows


def _parse_category_list_format(text: str) -> list[dict]:
    body = _section(text, "Top 20 Trending Products by Category")
    if not body:
        return []

    rows: list[dict] = []
    category: str | None = None
    item: dict | None = None
    detail_lines: list[str] = []

    def flush(item: dict | None, detail_lines: list[str]) -> None:
        if item is not None:
            item["signal_and_source"] = _strip_markdown_emphasis(
                " ".join(l.strip(" -") for l in detail_lines if l.strip())
            )
            rows.append(item)

    for raw_line in body.splitlines():
        line = raw_line.strip()
        heading_match = _CATEGORY_HEADING_RE.match(line)
        if heading_match:
            flush(item, detail_lines)
            item, detail_lines = None, []
            category = re.sub(r"^[^\w]+", "", heading_match.group(1)).strip()
            continue
        item_match = _LIST_ITEM_RE.match(line)
        if item_match:
            flush(item, detail_lines)
            item = dict(
                rank=int(item_match.group(1)),
                product=item_match.group(2).strip(),
                category=category,
            )
            detail_lines = []
            continue
        if line:
            detail_lines.append(line)
    flush(item, detail_lines)
    return rows


def _normalize_product_name(name: str) -> str:
    value = re.sub(r"\(.*?\)", "", name)  # drop parenthetical translations/notes
    value = re.sub(r"[^\w\s]", "", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def _industry_words(industry: str) -> list[str]:
    return [w.lower().rstrip("s") for w in re.findall(r"[\w-]+", industry) if len(w) > 2]


def _matches_industry(row: dict, words: list[str]) -> bool:
    text = f"{row.get('category') or ''} {row['product']} {row['signal_and_source']}".lower()
    return any(w in text for w in words)


def get_trending_products(
    region: str, industry: str | None = None, limit: int = 20, report_dir: Path | None = None
) -> list[dict]:
    """Top trending products for `region`, merged across every year found in
    data/raw/reports/ (currently 2025 + 2026), newest year winning on
    duplicate products. Returns [] if no report files are found for the
    region -- callers should treat that as "no data available", not an error.

    The curated reports span every consumer-product category (fashion,
    skincare, electronics, food, ...), not just one industry, so when
    `industry` is given the merged list is filtered down to rows that
    actually mention it -- otherwise an "Apparel & Fashion" trend list would
    get shown as-is under e.g. a Food & Beverages analysis. Returns []
    (rather than the unfiltered list) if nothing matches, since a generic
    top-20 list mislabeled as industry-specific is worse than no data.
    """
    files = _discover_report_files(region, report_dir)
    if not files:
        return []

    rows_by_year: dict[int, list[dict]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rows = _parse_table_format(text) or _parse_category_list_format(text)
        if not rows:
            continue
        year = _extract_year(path, text)
        for row in rows:
            row["year"] = year
            row["source_file"] = path.name
        rows_by_year.setdefault(year, []).extend(rows)

    merged: list[dict] = []
    seen: set[str] = set()
    for year in sorted(rows_by_year, reverse=True):
        for row in sorted(rows_by_year[year], key=lambda r: r["rank"]):
            key = _normalize_product_name(row["product"])
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(row)

    if industry:
        words = _industry_words(industry)
        if words:
            merged = [row for row in merged if _matches_industry(row, words)]

    merged = merged[:limit]
    for display_rank, row in enumerate(merged, start=1):
        row["display_rank"] = display_rank
    return merged
