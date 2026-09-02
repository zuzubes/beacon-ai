"""
Beacon AI
------------------
A minimalist internal tool for scanning macro-level trends emerging in the US
and China, drilling into the mega- and sub-trends they create, and surfacing
an investment recommendation lens for India.

Run with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import json
from pathlib import Path
from textwrap import dedent
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

from engine import (
    company_sectors,
    growth_companies,
    momentum,
    news,
    product_trends,
    research_search,
    trend_analysis,
    trends,
)
from engine.final_analysis_render import render_final_analysis_html


def _load_env_file() -> None:
    for env_path in (
        Path(__file__).with_name(".env"),
        Path(__file__).resolve().parent.parent / ".env",
    ):
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


_load_env_file()

st.set_page_config(
    page_title="Beacon AI",
    page_icon=str(Path(__file__).with_name("assets") / "favicon" / "favicon-32.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Minimalist styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
        :root {
            --paper: #f6efe3;
            --paper-2: #fbf7ef;
            --paper-3: #fffdf8;
            --ink: #1b2030;
            --muted: #6f6a61;
            --line: rgba(27, 32, 48, 0.12);
            --line-strong: rgba(27, 32, 48, 0.2);
            --accent: #d46334;
            --pine: #20423c;
            --ochre: #ca9726;
            --slate: #557096;
            --clay: #c94f31;
            --shadow: 0 20px 50px rgba(62, 35, 13, 0.08);
            --shadow-soft: 0 10px 25px rgba(62, 35, 13, 0.05);
            --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            --sans: "Source Sans 3", "Source Sans Pro", sans-serif;
            --sds-radius: 8px;
            --sds-shadow: 0px 1px 1px -0.5px rgba(49, 51, 63, 0.1), 0px 10px 5px -5px rgba(49, 51, 63, 0.1);
            --sds-success-bg: rgba(33, 195, 84, 0.1);
            --sds-success-text: #158237;
            --sds-info-bg: rgba(28, 131, 255, 0.1);
            --sds-info-text: #0054a3;
            --sds-warning-bg: rgba(255, 255, 18, 0.1);
            --sds-warning-text: #926c05;
            --sds-error-bg: rgba(255, 43, 43, 0.09);
            --sds-error-text: #bd4043;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 0% 0%, rgba(212, 99, 52, 0.08), transparent 32%),
                radial-gradient(circle at 100% 0%, rgba(85, 112, 150, 0.08), transparent 30%),
                linear-gradient(180deg, #f7f1e7 0%, #f4eee2 45%, #fbf8f1 100%);
            color: var(--ink);
        }
        html, body, [class*="css"] {
            font-family: var(--sans);
            color: var(--ink);
        }
        h1, h2, h3, h4 {
            font-family: var(--serif);
            letter-spacing: -0.03em;
            color: var(--ink);
        }
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(251, 247, 239, 0.98) 0%, rgba(245, 238, 224, 0.98) 100%);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] > div:first-child {
            background: transparent;
        }
        .brand-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 0.15rem;
        }
        .brand-logo {
            width: 72px;
            height: 72px;
            flex: 0 0 auto;
        }
        .brand-title {
            font-size: 3.1rem;
            line-height: 1;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.04em;
        }
        .page-hero {
            border: 1px solid var(--line);
            border-radius: 30px;
            background:
                linear-gradient(180deg, rgba(255, 253, 248, 0.88) 0%, rgba(247, 240, 229, 0.92) 100%);
            box-shadow: var(--shadow);
            padding: 28px 28px 22px;
            margin-bottom: 1.25rem;
            overflow: hidden;
        }
        .page-hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 0.8rem;
        }
        .page-hero-title {
            font-family: var(--serif);
            font-size: clamp(2.6rem, 4.6vw, 4.9rem);
            line-height: 0.92;
            letter-spacing: -0.05em;
            color: var(--ink);
            max-width: 12ch;
            margin-bottom: 0.75rem;
        }
        .page-hero-copy {
            max-width: 72ch;
            font-size: 1.06rem;
            line-height: 1.55;
            color: var(--muted);
            margin-bottom: 1rem;
        }
        .page-hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 1.1rem;
        }
        .tone-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.72);
            color: var(--ink);
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .page-hero-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }
        .hero-stat {
            border: 1px solid var(--line);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.76);
            padding: 14px 14px 13px;
            min-height: 88px;
            box-shadow: var(--shadow-soft);
        }
        .hero-stat-label {
            font-size: 0.71rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            color: var(--muted);
            margin-bottom: 0.35rem;
        }
        .hero-stat-value {
            font-size: 1.12rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
            word-break: break-word;
        }
        .hero-stat-copy {
            font-size: 0.83rem;
            line-height: 1.45;
            color: var(--muted);
        }

        .context-card {
            border: 1px solid #E2E8F0;
            border-radius: var(--sds-radius);
            padding: 14px 18px;
            background: #FAFBFC;
            margin-bottom: 1.2rem;
            display: flex;
            gap: 28px;
            flex-wrap: wrap;
            align-items: center;
        }
        .context-item { font-size: 0.85rem; color: #475569; }
        .context-item b { color: #0F172A; }

        .trend-card {
            border: 1px solid var(--line);
            border-radius: 26px;
            box-shadow: var(--shadow-soft);
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, rgba(251, 248, 241, 0.96) 100%);
            overflow: hidden;
        }
        .trend-card-inner {
            padding: 18px 18px 16px;
        }
        .trend-card-kicker {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 0.45rem;
        }
        .trend-card-title {
            font-family: var(--serif);
            font-size: 1.65rem;
            line-height: 1.02;
            letter-spacing: -0.04em;
            margin-bottom: 0.35rem;
            color: var(--ink);
        }
        .trend-card-parent {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
            margin-bottom: 0.7rem;
        }
        .trend-card-desc {
            font-size: 0.92rem;
            color: var(--ink);
            line-height: 1.55;
            margin-bottom: 0.95rem;
        }
        .trend-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
        }
        .trend-stat {
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.76);
            border-radius: 16px;
            padding: 10px 11px;
        }
        .trend-stat-label {
            font-size: 0.68rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 0.3rem;
        }
        .trend-stat-value {
            font-size: 1.02rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: var(--ink);
        }
        .trend-action-row {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: space-between;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .trend-action-note {
            font-size: 0.78rem;
            line-height: 1.4;
            color: var(--muted);
        }

        .pill { display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 0.74rem;
                font-weight: 600; margin-right: 6px; margin-bottom: 4px; }
        .pill-growth-pos { background: var(--sds-success-bg); color: var(--sds-success-text); }
        .pill-growth-neg { background: var(--sds-error-bg); color: var(--sds-error-text); }
        .pill-strength { background: rgba(85, 112, 150, 0.12); color: var(--slate); }
        .pill-horizon { background: rgba(202, 151, 38, 0.14); color: #8b6512; }
        .pill-invest { background: var(--sds-success-bg); color: var(--sds-success-text); }
        .pill-strategize { background: rgba(85, 112, 150, 0.12); color: var(--slate); }
        .pill-watch { background: var(--sds-warning-bg); color: var(--sds-warning-text); }
        .pill-stayaway { background: #F1F5F9; color: #64748B; }

        .signal-card {
            border: 1px solid var(--line);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.84);
            padding: 14px 16px;
            margin-bottom: 10px;
            box-shadow: var(--shadow-soft);
        }
        .signal-title { font-size: 1rem; font-weight: 800; color: var(--ink); margin-bottom: 4px; }
        .signal-meta { font-size: 0.76rem; color: var(--muted); }
        .signal-tag {
            display: inline-block;
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid var(--line);
            color: var(--ink);
            border-radius: 999px;
            padding: 3px 9px;
            font-size: 0.72rem;
            margin-right: 5px;
            margin-bottom: 6px;
        }

        /* News signal tile -- fixed-frame thumbnail (background-image + cover, so mixed source
           aspect ratios crop consistently instead of the tile stretching to fit the image). */
        .news-row {
            display: flex;
            gap: 16px;
            align-items: flex-start;
            padding: 14px;
            border: 1px solid var(--line);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.84);
            margin-bottom: 10px;
            box-shadow: var(--shadow-soft);
        }
        .news-thumb-link { flex: 0 0 auto; display: block; }
        .news-thumb { width: 160px; height: 110px; border-radius: 14px; background-color: #F1F5F9;
                      background-size: cover; background-position: center; flex: 0 0 auto; }
        .news-thumb.news-thumb-empty {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #94A3B8;
            font-size: 0.72rem;
            border: 1px solid var(--line);
        }
        .news-body { flex: 1 1 auto; min-width: 0; }
        .news-keywords { font-size: 0.76rem; color: #64748B; margin-bottom: 6px; }
        .news-keywords .dot { margin: 0 6px; color: #CBD5E1; }
        .news-title, .news-title:link, .news-title:visited {
            display: block;
            font-size: 1.04rem;
            font-weight: 800;
            color: var(--ink);
            text-decoration: none;
            line-height: 1.4;
            margin-bottom: 6px;
        }
        .news-title:hover { color: var(--accent); text-decoration: none; }
        .news-meta { display: flex; align-items: center; font-size: 0.8rem; color: #64748B; }
        .news-meta .dot { margin: 0 6px; color: #CBD5E1; }
        .news-avatar { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px;
                      border-radius: 50%; color: #FFFFFF; font-size: 0.62rem; font-weight: 700; margin-right: 6px; flex: 0 0 auto; }

        /* "Showing sample data" is informational, not a warning — mapped to the kit's st.info tokens. */
        .sample-banner {
            background: var(--sds-info-bg);
            border: none;
            color: var(--sds-info-text);
            border-radius: 18px;
            padding: 12px 16px;
            font-size: 0.84rem;
            margin-bottom: 14px;
        }
        .loading-banner {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid var(--line);
            color: var(--ink);
            border-radius: 18px;
            padding: 11px 14px;
            font-size: 0.84rem;
            margin: 1rem 0 1.25rem;
        }
        .empty-state {
            text-align: center;
            padding: 70px 20px;
            color: var(--muted);
        }
        .landing-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 1rem;
        }
        .landing-card {
            border: 1px solid var(--line);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.76);
            padding: 18px;
            box-shadow: var(--shadow-soft);
        }
        .landing-card-title {
            font-family: var(--serif);
            font-size: 1.45rem;
            line-height: 1.02;
            letter-spacing: -0.03em;
            color: var(--ink);
            margin-bottom: 0.45rem;
        }
        .landing-card-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .analysis-report {
            border: 1px solid var(--line);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        .analysis-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 18px 20px;
            border-bottom: 1px solid var(--line);
            background: linear-gradient(180deg, rgba(248, 242, 230, 0.9) 0%, rgba(255, 255, 255, 0.9) 100%);
        }
        .analysis-header-title {
            font-family: var(--serif);
            font-size: 1.32rem;
            font-weight: 700;
            color: var(--ink);
            letter-spacing: -0.03em;
            margin-bottom: 3px;
        }
        .analysis-header-meta {
            font-size: 0.82rem;
            color: var(--muted);
            display: flex;
            flex-wrap: wrap;
            gap: 10px 14px;
        }
        .analysis-actionbar {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            flex: 0 0 auto;
        }
        .analysis-action {
            width: 42px;
            height: 42px;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.92);
            color: var(--ink);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            box-shadow: var(--shadow-soft);
            font-size: 18px;
        }
        .analysis-action:hover { color: var(--accent); border-color: var(--accent); }
        .analysis-body { padding: 20px; }

        .hierarchy-overview {
            border: 1px solid var(--line);
            border-radius: 26px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.86) 0%, rgba(250, 245, 236, 0.94) 100%);
            box-shadow: var(--shadow);
            padding: 18px 20px;
            margin-bottom: 1.25rem;
        }
        .hierarchy-overview-title {
            font-family: var(--serif);
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--ink);
            letter-spacing: -0.03em;
            margin-bottom: 4px;
        }
        .hierarchy-overview-subtitle {
            font-size: 0.84rem;
            color: var(--muted);
            margin-bottom: 14px;
        }
        .hierarchy-metric-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 18px;
        }
        .hierarchy-metric {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.8);
            padding: 10px 14px;
            min-width: 120px;
        }
        .hierarchy-metric-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            margin-bottom: 4px;
        }
        .hierarchy-metric-value {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.02em;
        }
        .hierarchy-macro {
            border: 1px solid var(--line);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.84);
            box-shadow: var(--shadow-soft);
            padding: 14px 16px;
            margin-bottom: 14px;
        }
        .hierarchy-macro-title {
            font-family: var(--serif);
            font-size: 1.28rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 2px;
        }
        .hierarchy-macro-meta {
            font-size: 0.76rem;
            color: var(--muted);
            margin-bottom: 10px;
        }
        .hierarchy-macro-desc {
            font-size: 0.92rem;
            line-height: 1.55;
            color: var(--ink);
            margin-bottom: 12px;
        }
        .hierarchy-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        .hierarchy-chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.82);
            color: var(--ink);
            padding: 3px 9px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .hierarchy-mega-label {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 4px;
        }
        .hierarchy-mega-desc {
            font-size: 0.8rem;
            line-height: 1.45;
            color: var(--muted);
        }
        .drilldown-ready {
            border: 1px solid rgba(212, 99, 52, 0.22);
            background: rgba(212, 99, 52, 0.08);
            color: #7a3b1a;
            border-radius: 16px;
            padding: 10px 14px;
            font-size: 0.84rem;
            margin-bottom: 14px;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--line) !important;
            border-radius: 26px !important;
            background: rgba(255, 255, 255, 0.78) !important;
            box-shadow: var(--shadow-soft);
        }
        [data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.2rem;
        }
        [data-baseweb="tab-list"] {
            gap: 6px;
            background: transparent;
            border-bottom: 1px solid var(--line);
        }
        [data-baseweb="tab"] {
            font-family: var(--sans);
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--muted);
            letter-spacing: 0.01em;
            padding-top: 0.8rem;
            padding-bottom: 0.9rem;
        }
        [data-baseweb="tab"][aria-selected="true"] {
            color: var(--accent);
        }
        [data-baseweb="tab-highlight"] {
            background: var(--accent);
        }
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {
            border-radius: 999px;
            border: 1px solid var(--line-strong);
            background: var(--ink);
            color: #fff8ef;
            font-weight: 700;
            padding-top: 0.6rem;
            padding-bottom: 0.6rem;
            box-shadow: var(--shadow-soft);
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            border-color: var(--accent);
            background: var(--accent);
            color: #fffaf1;
        }
        [data-testid="stButton"] button:disabled,
        [data-testid="stDownloadButton"] button:disabled {
            background: rgba(27, 32, 48, 0.1);
            color: rgba(27, 32, 48, 0.35);
            border-color: rgba(27, 32, 48, 0.08);
            box-shadow: none;
        }
        @media (max-width: 960px) {
            .page-hero-grid,
            .landing-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .page-hero-title {
                max-width: none;
            }
        }
        @media (max-width: 720px) {
            .page-hero-grid,
            .landing-grid,
            .trend-stat-grid {
                grid-template-columns: 1fr;
            }
            .news-row {
                flex-direction: column;
            }
            .news-thumb {
                width: 100%;
                height: 180px;
            }
            .page-hero {
                padding: 22px 18px 18px;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

REC_PILL_CLASS = {
    "Invest": "pill-invest",
    "Strategize": "pill-strategize",
    "Watch": "pill-watch",
    "Stay away": "pill-stayaway",
}

TIME_RANGE_OPTIONS = ["Past 3 days", "Past 1 week", "Past 2 weeks", "Past 1 month"]
REGION_OPTIONS = ["US & China (Both)", "United States", "China"]
INDUSTRY_OPTIONS = [
    ("apparel_and_fashion", "Apparel & Fashion"),
    ("beauty_and_cosmetics", "Beauty & Cosmetics"),
    ("consumer_electronics", "Consumer Electronics"),
    ("ecology_and_environment", "Ecology & Environment"),
    ("entertainment", "Entertainment"),
    ("farms_and_ranches", "Farms & Ranches"),
    ("food_and_beverages", "Food & Beverages"),
    ("information_technology", "Information Technology"),
    ("jewelry_and_luxury_products", "Jewelry & Luxury Products"),
    ("sporting_goods", "Sporting Goods"),
    ("wellness", "Wellness"),
    ("wine_and_spirits", "Wine & Spirits"),
]


def _slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "custom_sector"


def _trend_counts(trends_data: list[dict] | None) -> dict[str, int]:
    counts = {"Macro": 0, "Mega": 0, "Sub": 0}
    for trend in trends_data or []:
        tier = trend.get("tier")
        if tier in counts:
            counts[tier] += 1
    return counts


def render_page_hero(context: dict | None, trends_data: list[dict] | None = None) -> None:
    counts = _trend_counts(trends_data)
    if context:
        company = html.escape(context.get("company") or "Beacon AI")
        time_range = html.escape(context.get("time_range") or "Past 1 week")
        region = html.escape(context.get("region") or "United States")
        industry = html.escape(context.get("industry") or "All sectors")
        copy = (
            "Macro, mega, and sub-trends mapped into a single editorial workflow, "
            "with momentum, news, and the summary report layered on top."
        )
    else:
        company = "Beacon AI"
        time_range = "Past 1 week"
        region = "US & China"
        industry = "Trend intelligence"
        copy = (
            "A Beacon editorial dashboard for reading the signal from macro, mega, and sub-trends "
            "before moving into momentum, news, and drill-down analysis."
        )
    scope_chip = f"<span class='tone-chip'>{industry}</span>" if context else ""

    stats_html = dedent(
        f"""
        <div class="page-hero-grid">
            <div class="hero-stat">
                <div class="hero-stat-label">Macro</div>
                <div class="hero-stat-value">{counts["Macro"]}</div>
                <div class="hero-stat-copy">Long-horizon forces shaping the market.</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-label">Mega</div>
                <div class="hero-stat-value">{counts["Mega"]}</div>
                <div class="hero-stat-copy">The tension points where macro forces collide.</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-label">Sub</div>
                <div class="hero-stat-value">{counts["Sub"]}</div>
                <div class="hero-stat-copy">The actionable trend tiles that feed drill-down.</div>
            </div>
            <div class="hero-stat">
                <div class="hero-stat-label">Scope</div>
                <div class="hero-stat-value">{company}</div>
                <div class="hero-stat-copy">{time_range} · {region}</div>
            </div>
        </div>
        """
    )

    st.markdown(
        dedent(
            f"""
            <section class="page-hero">
                <div class="page-hero-kicker">Beacon AI trend system</div>
                <div class="page-hero-title">The signal, ahead of the crowd.</div>
                <div class="page-hero-copy">{copy}</div>
                <div class="page-hero-meta">
                    <span class="tone-chip">Trend Hierarchy</span>
                    <span class="tone-chip">Momentum</span>
                    <span class="tone-chip">News Signals</span>
                    <span class="tone-chip">Drill-Down</span>
                    <span class="tone-chip">Summary Report</span>
                    {scope_chip}
                </div>
                {stats_html}
            </section>
            """
        ),
        unsafe_allow_html=True,
    )


st.session_state.setdefault("industry_options", list(INDUSTRY_OPTIONS))

# ---------------------------------------------------------------------------
# Sidebar — query inputs
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### New Analysis")
    openai_key_default = os.getenv("openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")
    newsapi_key_default = os.getenv("NEWSAPI_KEY", "") or os.getenv("NEWS_API_KEY", "")
    serper_key_default = os.getenv("SERPER_API_KEY", "") or os.getenv("serper_api_key", "")
    serpapi_key_default = os.getenv("SERP_API_KEY", "") or os.getenv("SERPAPI_API_KEY", "") or os.getenv("serp_api_key", "")
    tavily_key_default = os.getenv("TAVILY_API_KEY", "") or os.getenv("tavily_api_key", "")
    deepl_key_default = os.getenv("DEEPL_API_KEY", "") or os.getenv("deepl_api_key", "")

    company = st.text_input("Company / Fund", value="", placeholder="e.g. Northstar Micro Fund")
    detect_clicked = st.button("Detect Industry from Website", use_container_width=True)
    if detect_clicked:
        with st.spinner("Looking up their website..."):
            detection = company_sectors.detect_company_sectors(
                company,
                serper_key_default or None,
                serpapi_key_default or None,
                tavily_key_default or None,
                openai_key_default or None,
            )
        if detection.error:
            st.warning(detection.error)
        else:
            existing_slugs = {slug for slug, _ in st.session_state["industry_options"]}
            existing_labels = {label.strip().lower() for _, label in st.session_state["industry_options"]}
            new_entries = []
            for raw_label in detection.sectors:
                label = raw_label.strip().title()
                slug = _slugify(label)
                if slug in existing_slugs or label.lower() in existing_labels:
                    continue
                new_entries.append((slug, label))
                existing_slugs.add(slug)
            if new_entries:
                st.session_state["industry_options"] = new_entries + st.session_state["industry_options"]
            st.session_state["industry_select"] = _slugify(detection.sectors[0])
            st.success(f"Detected sector: {detection.sectors[0].title()}")

    time_range = st.selectbox("Time Range", TIME_RANGE_OPTIONS, index=1)
    region = st.selectbox("Region", REGION_OPTIONS, index=0)
    industry_options = st.session_state["industry_options"]
    industry_labels = dict(industry_options)
    industry = st.selectbox(
        "Industry / Sector",
        options=[value for value, _ in industry_options],
        format_func=lambda value: industry_labels.get(value, value),
        key="industry_select",
    )
    run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

brand_logo = Path(__file__).with_name("assets") / "beacon-ai-logo.png"
st.image(str(brand_logo), width=320)
st.caption("Macro trends in the US & China, mapped to India investment signal.")

loading_slot = st.empty()

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

if run_clicked:
    warnings = []
    use_live_llm = bool(openai_key_default)
    use_live_news = bool(newsapi_key_default)
    use_live_research = bool(serper_key_default or serpapi_key_default or tavily_key_default or deepl_key_default)
    industry_label = industry_labels.get(industry, industry) or "All sectors"
    loading_slot.markdown(
        '<div class="loading-banner">Building research context and trend report...</div>',
        unsafe_allow_html=True,
    )

    research_context = None
    if use_live_research:
        try:
            research_context = research_search.build_research_context(
                industry_label,
                region,
                time_range,
                serper_api_key=serper_key_default or None,
                serp_api_key=serpapi_key_default or None,
                tavily_api_key=tavily_key_default or None,
                deepl_api_key=deepl_key_default or None,
            )
        except Exception:  # noqa: BLE001
            warnings.append("We couldn't load the latest research, so this run uses general context instead.")
    st.session_state["research_context"] = research_context

    trend_data = None
    if use_live_llm and openai_key_default:
        try:
            trend_data = trends.call_live_trends(
                time_range,
                region,
                industry_label,
                openai_key_default,
                research_context.prompt if research_context else None,
            )
        except Exception:  # noqa: BLE001
            warnings.append("We couldn't generate a live trend read, so sample trend data is shown instead.")

    if trend_data is None:
        try:
            trend_data = trends.generate_mock_trends(time_range, region, industry)
        except Exception:  # noqa: BLE001
            # Last-resort fallback so a bug here can never leave the page silently stuck on
            # "No analysis yet" -- session_state always gets populated by the end of this block.
            warnings.append("Something went wrong while preparing the results. Please try again.")
            trend_data = []

    analysis_result = None
    try:
        analysis_result = trend_analysis.build_trend_analysis_report(
            time_range,
            region,
            industry_label,
            trend_data,
            research_context,
            api_key=openai_key_default or None,
        )
    except Exception:  # noqa: BLE001
        warnings.append("We couldn't build the final analysis report, so the app will show the trend view only.")

    loading_slot.markdown(
        '<div class="loading-banner">Scanning macro, mega, and sub-trends...</div>',
        unsafe_allow_html=True,
    )
    news_data = None
    if use_live_news and newsapi_key_default:
        try:
            news_data = news.call_live_news(
                time_range,
                industry_label,
                newsapi_key_default,
                region=region,
                count=8,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append("We couldn't fetch live news for this query, so sample articles are shown instead.")

    if news_data is None:
        try:
            news_data = news.generate_mock_news("", time_range, region, industry_label, count=8)
        except Exception:  # noqa: BLE001
            warnings.append("Something went wrong while preparing the news signals. Please try again.")
            news_data = []

    st.session_state["trends"] = trend_data
    st.session_state["news"] = news_data
    st.session_state["analysis_result"] = analysis_result
    st.session_state["is_mock_trends"] = not (use_live_llm and openai_key_default and trend_data is not None)
    st.session_state["is_mock_news"] = not (use_live_news and newsapi_key_default and news_data is not None)
    st.session_state["warnings"] = warnings
    st.session_state["context"] = dict(
        company=company or "Unnamed analysis",
        time_range=time_range,
        region=region,
        industry=industry_label,
    )
    loading_slot.empty()

if "trends" not in st.session_state:
    render_page_hero(None, None)
    st.markdown(
        dedent(
            """
            <div class="landing-grid">
                <div class="landing-card">
                    <div class="landing-card-title">Set the frame</div>
                    <div class="landing-card-copy">Choose a company or fund, then pick the time range, region, and sector from the sidebar.</div>
                </div>
                <div class="landing-card">
                    <div class="landing-card-title">Read the hierarchy</div>
                    <div class="landing-card-copy">The Trend Hierarchy view lands on a compact map of macro, mega, and sub-trends.</div>
                </div>
                <div class="landing-card">
                    <div class="landing-card-title">Open the drill-down</div>
                    <div class="landing-card-copy">Generate company, social, and product signals from any sub-trend tile.</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    st.stop()

ctx = st.session_state["context"]

research_context = st.session_state.get("research_context")
if research_context and research_context.providers_used:
    st.caption("This analysis was informed by live, up-to-date research.")

render_page_hero(ctx, st.session_state.get("trends"))

all_trends = st.session_state["trends"]
all_news = st.session_state["news"]
analysis_result = st.session_state.get("analysis_result")
page_errors: list[str] = []

# ---------------------------------------------------------------------------
# Card renderer
# ---------------------------------------------------------------------------


def render_trend_card(t: dict, show_drilldown_action: bool = False) -> None:
    growth_class = "pill-growth-pos" if t["growth_pct"] >= 0 else "pill-growth-neg"
    growth_sign = "▲" if t["growth_pct"] >= 0 else "▼"
    rec_class = REC_PILL_CLASS.get(t["recommendation"], "pill-watch")
    with st.container(border=True):
        st.markdown(
            dedent(
                f"""
                <div class="trend-card-inner">
                    <div class="trend-card-kicker">{html.escape(t['tier'])} trend</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        left_col, right_col = st.columns([3, 1], vertical_alignment="top")
        with left_col:
            st.markdown(f"<div class='trend-card-title'>{html.escape(t['name'])}</div>", unsafe_allow_html=True)
            if t.get("parent"):
                st.markdown(f"<div class='trend-card-parent'>via {html.escape(t['parent'])}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='trend-card-desc'>{html.escape(t['description'])}</div>", unsafe_allow_html=True)
            st.markdown(
                " ".join(
                    [
                        f"<span class='pill {growth_class}'>{growth_sign} {t['growth_pct']:+.0f}%</span>",
                        f"<span class='pill pill-strength'>Strength {t['strength']:.1f}</span>",
                        f"<span class='pill pill-horizon'>{html.escape(t['time_horizon'])}</span>",
                        f"<span class='pill {rec_class}'>{html.escape(t['recommendation'])}</span>",
                    ]
                ),
                unsafe_allow_html=True,
            )
        with right_col:
            st.markdown(
                dedent(
                    f"""
                    <div class="trend-stat-grid">
                        <div class="trend-stat">
                            <div class="trend-stat-label">Growth</div>
                            <div class="trend-stat-value">{growth_sign} {t['growth_pct']:+.0f}%</div>
                        </div>
                        <div class="trend-stat">
                            <div class="trend-stat-label">Strength</div>
                            <div class="trend-stat-value">{t['strength']:.1f}</div>
                        </div>
                        <div class="trend-stat">
                            <div class="trend-stat-label">Horizon</div>
                            <div class="trend-stat-value">{html.escape(t['time_horizon'])}</div>
                        </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        if show_drilldown_action and t["tier"] == "Sub":
            st.markdown(
                dedent(
                    """
                    <div class="trend-action-row">
                        <div class="trend-action-note">Generate the sub-trend drill-down from this tile.</div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
            if st.button("Generate drill-down", key=f"subtrend_generate::{t['id']}", use_container_width=True):
                selected_sub_id = t["id"]
                st.session_state["drilldown_subtrend_select"] = selected_sub_id
                st.session_state["drilldown_product_region"] = _default_product_region()
                payload = build_drilldown_payload(t, _default_product_region())
                st.session_state[_drilldown_cache_key(selected_sub_id, _default_product_region())] = payload
                st.session_state["drilldown_last_generated"] = selected_sub_id


def render_trend_grid(items: list[dict], columns: int = 3, show_drilldown_action: bool = False) -> None:
    if not items:
        render_empty_state("No content is available in this section yet.")
        return
    cols = st.columns(columns)
    for i, t in enumerate(items):
        with cols[i % columns]:
            render_trend_card(t, show_drilldown_action=show_drilldown_action)


AVATAR_PALETTE = ["#4F46E5", "#059669", "#DC2626", "#D97706", "#0891B2", "#7C3AED", "#DB2777", "#65A30D"]


def _relative_time(hours_ago: int | None) -> str:
    if not isinstance(hours_ago, int) or hours_ago >= 9999:
        return "recently"
    if hours_ago < 1:
        return "just now"
    if hours_ago < 24:
        return f"{hours_ago} hour{'s' if hours_ago != 1 else ''} ago"
    days = hours_ago // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def _avatar_color(source: str) -> str:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return AVATAR_PALETTE[int(digest[:8], 16) % len(AVATAR_PALETTE)]


def _safe_url(url: str | None) -> str | None:
    if url and url.startswith(("http://", "https://")):
        return url
    return None


def _strip_leading_heading(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines)


def render_news_card(article: dict) -> None:
    title = html.escape(article.get("title") or "Untitled")
    source = html.escape(article.get("source") or "Unknown source")
    when = _relative_time(article.get("hours_ago"))
    url = _safe_url(article.get("url"))
    image_url = _safe_url(article.get("urlToImage"))

    keywords = [html.escape(k) for k in article.get("tags", [])][:3]
    extra = len(article.get("tags", [])) - len(keywords)
    if keywords:
        keywords_html = f"<span class='dot'>&bull;</span>".join(f"<span>{k}</span>" for k in keywords)
        if extra > 0:
            keywords_html += f"<span class='dot'>&bull;</span><span>+{extra}</span>"
        keywords_row = f"<div class='news-keywords'>{keywords_html}</div>"
    else:
        keywords_row = ""

    title_open, title_close = (f"<a class='news-title' href='{url}' target='_blank' rel='noopener noreferrer'>", "</a>") if url else ("<span class='news-title'>", "</span>")

    if image_url:
        thumb = f"background-image:url('{html.escape(image_url, quote=True)}')"
        thumb_html = f"<div class='news-thumb' style=\"{thumb}\"></div>"
    else:
        thumb_html = "<div class='news-thumb news-thumb-empty'>No image</div>"
    if url:
        thumb_html = f"<a class='news-thumb-link' href='{url}' target='_blank' rel='noopener noreferrer'>{thumb_html}</a>"
    else:
        thumb_html = f"<div class='news-thumb-link'>{thumb_html}</div>"

    initial = html.escape(source[:1].upper() or "?")
    avatar = f"<span class='news-avatar' style='background:{_avatar_color(source)}'>{initial}</span>"

    st.markdown(
        dedent(
            f"""
            <div class="news-row">
                {thumb_html}
                <div class="news-body">
                    {keywords_row}
                    {title_open}{title}{title_close}
                    <div class="news-meta">{avatar}{source}<span class="dot">&bull;</span>{when}</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_company_card(company: dict) -> None:
    name = html.escape(company.get("name") or "Unknown")
    reason = html.escape(company.get("growth_reason") or "")
    growth_pct = company.get("growth_pct")
    meta = f"Est. growth +{float(growth_pct):.0f}%" if isinstance(growth_pct, (int, float)) else ""
    st.markdown(
        dedent(
            f"""
            <div class="signal-card">
                <div class="signal-title">{name}</div>
                <div class="signal-meta">{html.escape(meta)}</div>
                <div style="margin-top:6px;font-size:0.88rem;color:var(--ink);line-height:1.45;">{reason}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _default_product_region() -> str:
    return "China" if ctx["region"] == "China" else "United States"


def _drilldown_cache_key(subtrend_id: str, product_region: str) -> str:
    return f"drilldown::{subtrend_id}::{ctx['region']}::{product_region}"


def build_drilldown_payload(selected_sub: dict, product_region: str) -> dict:
    use_live = bool(openai_key_default)
    use_live_research_dd = bool(serper_key_default or serpapi_key_default or tavily_key_default or deepl_key_default)

    research_prompt = None
    if use_live and use_live_research_dd:
        try:
            drilldown_research = research_search.build_research_context(
                f"{selected_sub['name']} ({ctx['industry']})",
                ctx["region"],
                ctx["time_range"],
                serper_api_key=serper_key_default or None,
                serp_api_key=serpapi_key_default or None,
                tavily_api_key=tavily_key_default or None,
                deepl_api_key=deepl_key_default or None,
            )
            research_prompt = drilldown_research.prompt
        except Exception:  # noqa: BLE001
            research_prompt = None

    companies, companies_is_sample = None, True
    if use_live:
        try:
            companies = growth_companies.call_live_companies(
                selected_sub["name"], ctx["industry"], ctx["region"], openai_key_default, research_prompt
            )
            companies_is_sample = not companies
        except Exception:  # noqa: BLE001
            companies = None
    if not companies:
        companies = growth_companies.generate_mock_companies(selected_sub["name"], ctx["industry"], ctx["region"])
        companies_is_sample = True

    social, social_is_sample = None, True
    if use_live:
        try:
            social = growth_companies.call_live_social_signals(
                selected_sub["name"], ctx["industry"], ctx["region"], openai_key_default, ctx["time_range"]
            )
            social_is_sample = False
        except Exception:  # noqa: BLE001
            social = None
    if not social:
        social = growth_companies.generate_mock_social_signals(selected_sub["name"], ctx["industry"], ctx["region"])
        social_is_sample = True

    products = product_trends.get_trending_products(product_region, ctx["industry"])
    return dict(
        companies=companies,
        companies_is_sample=companies_is_sample,
        social=social,
        social_is_sample=social_is_sample,
        products=products,
        product_region=product_region,
    )


def render_drilldown_results(cached: dict) -> None:
    st.markdown("### Top Growing Companies")
    if cached["companies_is_sample"]:
        st.markdown(
            '<div class="sample-banner">Sample companies. Add an OpenAI key to .env for a live list.</div>',
            unsafe_allow_html=True,
        )
    if not cached["companies"]:
        render_empty_state("No companies were returned for this query.")
    for company in cached["companies"]:
        render_company_card(company)

    st.markdown("### Social Signal")
    st.caption("AI-estimated, directional signal -- not a live TikTok, Instagram, or Reddit pull.")
    if cached["social_is_sample"]:
        st.markdown(
            '<div class="sample-banner">Sample social signals. Add an OpenAI key to .env for a live estimate.</div>',
            unsafe_allow_html=True,
        )
    social_cols = st.columns(2)
    with social_cols[0]:
        st.markdown("**TikTok hashtags**")
        render_hashtags(cached["social"]["tiktok_hashtags"])
    with social_cols[1]:
        st.markdown("**Instagram hashtags**")
        render_hashtags(cached["social"]["instagram_hashtags"])
    st.markdown("**Reddit signal**")
    reddit_signals = cached["social"]["reddit_signals"]
    if not reddit_signals:
        st.caption("No Reddit signals available.")
    for post in reddit_signals:
        render_reddit_signal(post)

    st.markdown(f"### Top Trending Products - {cached['product_region']}")
    if not cached["products"]:
        render_empty_state(
            f"No trending-product data mentioning {html.escape(ctx['industry'])} was found for "
            f"{html.escape(cached['product_region'])} yet."
        )
    else:
        rows = [
            {
                "#": p["display_rank"],
                "Product": p["product"],
                "Signal / Source": p["signal_and_source"],
                "Year": p["year"],
            }
            for p in cached["products"]
        ]
        st.dataframe(
            rows,
            hide_index=True,
            use_container_width=True,
            column_config={
                "#": st.column_config.NumberColumn(width="small"),
                "Product": st.column_config.TextColumn(width="medium"),
                "Signal / Source": st.column_config.TextColumn(width="large"),
                "Year": st.column_config.NumberColumn(width="small"),
            },
        )


def render_subtrend_explorer(sub_trends: list[dict]) -> None:
    st.caption(
        "Pick a sub-trend to generate the company, social, and product drill-down for this region."
    )
    if not sub_trends:
        render_empty_state("No drill-down content is available yet. Run an analysis to populate it.")
        return

    sub_trend_by_id = {t["id"]: t for t in sub_trends}
    selected_sub_id = st.selectbox(
        "Sub-trend",
        options=list(sub_trend_by_id.keys()),
        format_func=lambda sid: sub_trend_by_id[sid]["name"],
        key="drilldown_subtrend_select",
    )
    selected_sub = sub_trend_by_id[selected_sub_id]
    st.caption(selected_sub["description"])

    product_region = st.radio(
        "Trending-products region",
        ["United States", "China"],
        index=1 if ctx["region"] == "China" else 0,
        horizontal=True,
        key="drilldown_product_region",
    )

    cache_key = _drilldown_cache_key(selected_sub_id, product_region)
    generate_clicked = st.button("Generate drill-down", key=f"drilldown_generate::{selected_sub_id}::{product_region}")

    if generate_clicked:
        st.session_state["drilldown_subtrend_select"] = selected_sub_id
        st.session_state["drilldown_product_region"] = product_region
        st.session_state[cache_key] = build_drilldown_payload(selected_sub, product_region)

    cached = st.session_state.get(cache_key)
    if not cached:
        render_empty_state("Click Generate drill-down to load companies, social signals, and products.")
        return

    render_drilldown_results(cached)


def render_trend_hierarchy_overview(trends_data: list[dict]) -> None:
    macro_trends = [t for t in trends_data if t["tier"] == "Macro"]
    mega_trends = [t for t in trends_data if t["tier"] == "Mega"]
    sub_trends = [t for t in trends_data if t["tier"] == "Sub"]
    mega_by_parent: dict[str, list[dict]] = {}
    sub_by_parent: dict[str, list[dict]] = {}
    for trend in mega_trends:
        mega_by_parent.setdefault(trend["parent"] or "", []).append(trend)
    for trend in sub_trends:
        sub_by_parent.setdefault(trend["parent"] or "", []).append(trend)

    st.markdown(
        dedent(
            f"""
            <div class="hierarchy-overview">
                <div class="hierarchy-overview-title">Trend Hierarchy</div>
                <div class="hierarchy-overview-subtitle">
                    A compact landing page for the current macro, mega, and sub-trends. Open the Sub-Trend Drill-Down from
                    any sub-trend tile when you want to research companies and signals.
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        dedent(
            f"""
            <div class="hierarchy-metric-grid">
                <div class='hierarchy-metric'><div class='hierarchy-metric-label'>Macro trends</div><div class='hierarchy-metric-value'>{len(macro_trends)}</div></div>
                <div class='hierarchy-metric'><div class='hierarchy-metric-label'>Mega trends</div><div class='hierarchy-metric-value'>{len(mega_trends)}</div></div>
                <div class='hierarchy-metric'><div class='hierarchy-metric-label'>Sub-trends</div><div class='hierarchy-metric-value'>{len(sub_trends)}</div></div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    for macro in macro_trends:
        megas = mega_by_parent.get(macro["name"], [])
        with st.container(border=True):
            left_col, right_col = st.columns([3, 1], vertical_alignment="top")
            with left_col:
                st.markdown(
                    f"<div class='hierarchy-macro-title'>{html.escape(macro['name'])}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='hierarchy-macro-meta'>{html.escape(macro['category'])} · Strength {macro['strength']:.1f} · {html.escape(macro['time_horizon'])}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='hierarchy-macro-desc'>{html.escape(macro['description'])}</div>",
                    unsafe_allow_html=True,
                )
            with right_col:
                st.markdown(
                    dedent(
                        f"""
                        <div class="trend-stat">
                            <div class="trend-stat-label">Mega trends</div>
                            <div class="trend-stat-value">{len(megas)}</div>
                        </div>
                        <div style="height:8px"></div>
                        <div class="trend-stat">
                            <div class="trend-stat-label">Sub-trends</div>
                            <div class="trend-stat-value">{len(sub_by_parent.get(macro["name"], []))}</div>
                        </div>
                        """
                    ),
                    unsafe_allow_html=True,
                )
            if not megas:
                continue
            st.markdown("**Building blocks underneath this macro trend**")
            mega_cols = st.columns(min(max(len(megas), 1), 3))
            for i, mega in enumerate(megas):
                with mega_cols[i % len(mega_cols)]:
                    st.markdown(
                        f"<div class='hierarchy-mega-label'>{html.escape(mega['name'])}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='hierarchy-macro-meta'>Strength {mega['strength']:.1f} · {html.escape(mega['time_horizon'])}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='hierarchy-mega-desc'>{html.escape(mega['description'])}</div>",
                        unsafe_allow_html=True,
                    )
                    sub_items = sub_by_parent.get(mega["name"], [])
                    if sub_items:
                        chip_html = "".join(
                            f"<span class='hierarchy-chip'>{html.escape(sub['name'])}</span>" for sub in sub_items
                        )
                        st.markdown(f"<div class='hierarchy-chip-row'>{chip_html}</div>", unsafe_allow_html=True)
                    else:
                        st.caption("No sub-trends available.")


def render_hashtags(hashtags: list[str]) -> None:
    if not hashtags:
        st.caption("No hashtags available.")
        return
    tags_html = "".join(f'<span class="signal-tag">{html.escape(tag)}</span>' for tag in hashtags)
    st.markdown(tags_html, unsafe_allow_html=True)


def render_reddit_signal(post: dict) -> None:
    title = html.escape(post.get("title") or "Untitled")
    subreddit = html.escape(post.get("subreddit") or "")
    why = html.escape(post.get("why_relevant") or "")
    st.markdown(
        f"- **{title}** — {subreddit}<br><span style='color:var(--muted);font-size:0.82rem;'>{why}</span>",
        unsafe_allow_html=True,
    )


def render_empty_state(message: str) -> None:
    st.markdown(
        dedent(
            f"""
            <div class="empty-state">
                <h3>Nothing to show yet</h3>
                <p>{html.escape(message)}</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _analysis_pdf_bytes(result: object) -> bytes:
    pdf_path = getattr(result, "pdf_path", "")
    if pdf_path:
        path = Path(pdf_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        if path.exists():
            data = path.read_bytes()
            if data:
                return data
    return getattr(result, "pdf_bytes", b"") or b""


def _is_public_share_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and parsed.netloc in {"0x0.st", "transfer.sh"}


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

tab_hierarchy, tab_momentum, tab_news, tab_drilldown, tab_analysis = st.tabs(
    ["Trend Hierarchy", "Momentum", "News Signals", "Sub-Trend Drill-Down", "Summary Report"]
)

with tab_hierarchy:
    try:
        if st.session_state.get("is_mock_trends"):
            st.markdown(
                '<div class="sample-banner">Sample trend analysis. Add an OpenAI key to .env to load a live read.</div>',
                unsafe_allow_html=True,
            )

        overview_tab, macro_tab, mega_tab, sub_tab = st.tabs(
            ["Overview", "Macro-Trends", "Mega-Trends", "Sub-Trends"]
        )
        with overview_tab:
            render_trend_hierarchy_overview(all_trends)
        with macro_tab:
            st.caption("Long-term macro changes playing out across years to decades — the major forces shaping consumer and business behavior.")
            render_trend_grid([t for t in all_trends if t["tier"] == "Macro"])
        with mega_tab:
            st.caption("The building blocks of the arena — the tension points created where macro trends intersect with basic needs.")
            render_trend_grid([t for t in all_trends if t["tier"] == "Mega"])
        with sub_tab:
            st.caption("Emerging, actionable trends arising from that tension — where the market starts behaving differently.")
            render_trend_grid([t for t in all_trends if t["tier"] == "Sub"], show_drilldown_action=True)
            if st.session_state.get("drilldown_last_generated"):
                last_id = st.session_state["drilldown_last_generated"]
                last_name = next((t["name"] for t in all_trends if t["id"] == last_id), "that sub-trend")
                st.markdown(
                    f'<div class="drilldown-ready">Drill-down ready for <b>{html.escape(last_name)}</b>. Open the Sub-Trend Drill-Down tab to review the generated companies, social signals, and product signals.</div>',
                    unsafe_allow_html=True,
                )
    except Exception as exc:  # noqa: BLE001
        page_errors.append("Trend hierarchy is unavailable right now.")
        render_empty_state("The trend hierarchy is unavailable right now. Run a new analysis to try again.")

with tab_drilldown:
    try:
        if st.session_state.get("is_mock_trends"):
            st.markdown(
                '<div class="sample-banner">Sample drill-down. Add an OpenAI key to .env for a live read.</div>',
                unsafe_allow_html=True,
            )
        render_subtrend_explorer([t for t in all_trends if t["tier"] == "Sub"])
    except Exception as exc:  # noqa: BLE001
        page_errors.append("Sub-trend drill-down is unavailable right now.")
        render_empty_state("The sub-trend drill-down is unavailable right now. Run a new analysis to try again.")

with tab_momentum:
    try:
        if st.session_state.get("is_mock_trends"):
            st.markdown(
                '<div class="sample-banner">Momentum diagram uses the sample trend data above.</div>',
                unsafe_allow_html=True,
            )
        momentum_tab, radar_tab = st.tabs(["Momentum Diagram", "Trend Radar"])
        with momentum_tab:
            color_by = st.radio("Color by", ["Category", "Recommendation"], horizontal=True, label_visibility="collapsed")
            fig = momentum.build_momentum_figure(all_trends, color_by=color_by.lower())
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Radius = trend strength (0-10). Each colored rim segment groups one trend cluster; dot size shrinks from Macro to Sub-trend.")
        with radar_tab:
            fig = momentum.build_trend_radar_figure(all_trends)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Average strength by trend category, rendered as a radar-style summary.")
    except Exception as exc:  # noqa: BLE001
        page_errors.append("Momentum view is unavailable right now.")
        render_empty_state("The momentum view is unavailable right now. Run a new analysis to try again.")

with tab_news:
    try:
        if st.session_state.get("is_mock_news"):
            st.markdown(
                '<div class="sample-banner">Sample signals. Add a NewsAPI key to .env for live articles.</div>',
                unsafe_allow_html=True,
            )
        if not all_news:
            render_empty_state("No news signals are available for this query yet.")
        for a in all_news:
            render_news_card(a)
    except Exception as exc:  # noqa: BLE001
        page_errors.append("News signals are unavailable right now.")
        render_empty_state("The news signals view is unavailable right now. Run a new analysis to try again.")

with tab_analysis:
    try:
        if analysis_result is None:
            render_empty_state("No final analysis is available yet. Run an analysis to generate this tab.")
        else:
            share_target = analysis_result.share_url if _is_public_share_url(analysis_result.share_url) else None
            if not share_target:
                pdf_bytes = _analysis_pdf_bytes(analysis_result)
                if pdf_bytes:
                    share_target = trend_analysis._upload_public_pdf(
                        pdf_bytes,
                        Path(analysis_result.pdf_path).name,
                    )
            html_report = getattr(analysis_result, "html_report", None)
            if not html_report:
                html_report = render_final_analysis_html(
                    analysis_result.report_markdown,
                    analysis_result.combined_markdown,
                    all_trends,
                    research_context,
                    getattr(analysis_result, "generated_at", ""),
                    ctx["region"],
                    ctx["industry"],
                )
            button_cols = st.columns([1, 1, 6])
            with button_cols[0]:
                st.download_button(
                    "Download PDF",
                    data=_analysis_pdf_bytes(analysis_result),
                    file_name=Path(analysis_result.pdf_path).name,
                    mime="application/pdf",
                    use_container_width=True,
                )
            with button_cols[1]:
                if share_target:
                    share_button_html = dedent(
                        f"""
                        <button id="copy-link-btn" style="
                            width: 100%;
                            min-height: 2.5rem;
                            border: 1px solid #E2E8F0;
                            border-radius: 0.5rem;
                            background: #FFFFFF;
                            color: #0F172A;
                            font: inherit;
                            font-weight: 600;
                            cursor: pointer;
                        ">Copy link</button>
                        <script>
                          (() => {{
                            const url = {json.dumps(share_target)};
                            const btn = document.getElementById("copy-link-btn");
                            btn.addEventListener("click", async () => {{
                              try {{
                                await navigator.clipboard.writeText(url);
                                btn.textContent = "Copied";
                              }} catch (err) {{
                                btn.textContent = "Copy failed";
                              }}
                              window.setTimeout(() => {{
                                btn.textContent = "Copy link";
                              }}, 1500);
                            }});
                          }})();
                        </script>
                        """
                    )
                    components.html(share_button_html, height=44, scrolling=False)
                else:
                    st.button("Copy link", disabled=True, use_container_width=True)
            if not share_target:
                st.caption(
                    "Sharing needs a public URL. In local mode you can download the PDF, but the app "
                    "cannot generate a link other people can open."
                )
            else:
                st.caption("The report has a public URL. Use Copy link to share it.")
            components.html(html_report, height=1200, scrolling=True)
    except Exception as exc:  # noqa: BLE001
        page_errors.append("Final analysis is unavailable right now.")
        render_empty_state("The final analysis is unavailable right now. Run a new analysis to try again.")

bottom_messages = st.session_state.get("warnings", []) + page_errors
if bottom_messages:
    st.markdown("---")
    st.error("Some parts of this page are unavailable right now.")
    for message in bottom_messages:
        st.caption(message)
