"""Tests for engine/product_trends.py -- parsing the curated Top-20 trending-product
markdown reports under data/raw/reports/ (repo root)."""

from pathlib import Path

from engine import product_trends

TABLE_FORMAT_MD = """\
# Top 20 Trending Products in the US — 2026 Report

## Top 20 Table

| # | Product | Category | 2026 Growth Signal | Retail Price Band | Primary Source(s) |
|---|---------|----------|--------------------|-------------------|-------------------|
| 1 | Embroidered apparel | Fashion | +7,043% YoY | $25-$120 | GoDaddy |
| 2 | Exosome serum | Skincare | +6,400% YoY | $50-$300 | GoDaddy |

## Sources
Some other section that should not be parsed as table rows.
"""

CATEGORY_LIST_FORMAT_MD = """\
# Top 20 Trending Products Report

## Top 20 Trending Products by Category

### 🏥 Health & Wellness (2)

**1. GLP-1 support supplements**
- Trend signal: search growth 99X+.
- Driver: companion supplements for GLP-1 users.
- (Source: Exploding Topics, 2026)

**2. Creatine gummies**
- Trend signal: ~116K monthly searches.
- Driver: portable evolution of creatine powder.
- (Source: Techpoint, 2025)

### 💄 Beauty & Personal Care (1)

**3. PDRN serum**
- Trend signal: +5,500% over 5 years.
- Driver: salmon-DNA skincare ingredient.

## Methodology
Not part of the list.
"""


def test_parse_table_format_extracts_rank_and_product():
    rows = product_trends._parse_table_format(TABLE_FORMAT_MD)
    assert [r["rank"] for r in rows] == [1, 2]
    assert rows[0]["product"] == "Embroidered apparel"
    assert "GoDaddy" in rows[0]["signal_and_source"]


def test_parse_table_format_ignores_other_sections():
    rows = product_trends._parse_table_format(TABLE_FORMAT_MD)
    assert all("Sources" not in r["product"] for r in rows)


def test_parse_category_list_format_extracts_rank_product_and_category():
    rows = product_trends._parse_category_list_format(CATEGORY_LIST_FORMAT_MD)
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert rows[0]["product"] == "GLP-1 support supplements"
    assert rows[0]["category"] == "Health & Wellness"
    assert rows[2]["category"] == "Beauty & Personal Care"
    assert "companion supplements" in rows[0]["signal_and_source"]


def test_parse_table_format_returns_empty_for_category_list_doc():
    assert product_trends._parse_table_format(CATEGORY_LIST_FORMAT_MD) == []


def test_parse_category_list_format_returns_empty_for_table_doc():
    assert product_trends._parse_category_list_format(TABLE_FORMAT_MD) == []


def test_discover_report_files_matches_inconsistent_naming(tmp_path):
    (tmp_path / "US_Top20_Trending_Products_2026.md").write_text("x", encoding="utf-8")
    (tmp_path / "US-2025-Top20-Trending-Products-Report.md").write_text("x", encoding="utf-8")
    (tmp_path / "China_Top20_Trending_Products_2026.md").write_text("x", encoding="utf-8")
    (tmp_path / "unrelated.md").write_text("x", encoding="utf-8")

    us_files = product_trends._discover_report_files("United States", report_dir=tmp_path)
    assert {p.name for p in us_files} == {
        "US_Top20_Trending_Products_2026.md",
        "US-2025-Top20-Trending-Products-Report.md",
    }

    china_files = product_trends._discover_report_files("China", report_dir=tmp_path)
    assert {p.name for p in china_files} == {"China_Top20_Trending_Products_2026.md"}


def test_get_trending_products_merges_years_preferring_newest(tmp_path):
    (tmp_path / "US_Top20_Trending_Products_2026.md").write_text(
        "## Top 20 Table\n\n"
        "| # | Product | Signal |\n|---|---|---|\n"
        "| 1 | Widget A | new-signal |\n"
        "| 2 | Widget B | new-signal |\n",
        encoding="utf-8",
    )
    (tmp_path / "US_Top20_Trending_Products_2025.md").write_text(
        "## Top 20 Table\n\n"
        "| # | Product | Signal |\n|---|---|---|\n"
        "| 1 | Widget A | old-signal |\n"
        "| 2 | Widget C | old-signal |\n",
        encoding="utf-8",
    )

    rows = product_trends.get_trending_products("United States", report_dir=tmp_path)
    names = [r["product"] for r in rows]
    assert names == ["Widget A", "Widget B", "Widget C"]
    # Widget A appears in both years -- the newer (2026) row must win.
    widget_a = next(r for r in rows if r["product"] == "Widget A")
    assert widget_a["year"] == 2026
    assert widget_a["signal_and_source"] == "new-signal"
    assert [r["display_rank"] for r in rows] == [1, 2, 3]


def test_get_trending_products_returns_empty_when_no_files_found(tmp_path):
    assert product_trends.get_trending_products("United States", report_dir=tmp_path) == []


def test_get_trending_products_against_real_report_files():
    for region in ("United States", "China"):
        rows = product_trends.get_trending_products(region)
        assert len(rows) == 20
        assert [r["display_rank"] for r in rows] == list(range(1, 21))
        assert all(r["product"] for r in rows)


def test_default_report_dir_points_at_repo_root_data_folder():
    assert product_trends.DEFAULT_REPORT_DIR == (
        Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "reports"
    )
    assert product_trends.DEFAULT_REPORT_DIR.exists()
