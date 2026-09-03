"""Company-website sector detection for Beacon AI.

Given a company/fund name, finds their official website, reads the homepage,
and asks the OpenAI API to classify which industries/sectors they invest in,
constrained to the taxonomy in data/raw/Inspirations/industry.txt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import requests

from engine.research_search import find_official_website

INDUSTRY_TAXONOMY_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "Inspirations" / "industry.txt"
)


def _load_industry_taxonomy() -> list[str]:
    try:
        lines = INDUSTRY_TAXONOMY_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:  # noqa: BLE001
        return []
    return [line.strip() for line in lines if line.strip()]


INDUSTRY_TAXONOMY = _load_industry_taxonomy()

FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MODEL = "gpt-4.1-mini"
# A fund's sector focus ("focus areas" / "investment thesis") is usually spelled out on an
# About/Focus/Portfolio page, not always the homepage itself -- these are the link-text/href
# hints used to find and pull that page in alongside the homepage.
ABOUT_LINK_HINTS = ("about", "focus", "thesis", "what-we-do", "portfolio", "invest")


@dataclass(frozen=True)
class SectorDetectionResult:
    website: str | None
    sectors: list[str] = field(default_factory=list)
    error: str | None = None  # plain-language; safe to show the user as-is


def _fetch_soup(url: str):
    from bs4 import BeautifulSoup

    resp = requests.get(url, headers=FETCH_HEADERS, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser"), resp.url


def _visible_text(soup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def _find_about_link(soup, base_url: str) -> str | None:
    for a in soup.find_all("a", href=True):
        haystack = f"{a.get_text() or ''} {a['href']}".strip().lower()
        if any(hint in haystack for hint in ABOUT_LINK_HINTS):
            return urljoin(base_url, a["href"])
    return None


def _fetch_company_text(url: str) -> str | None:
    """Homepage text, plus an About/Focus/Portfolio page's text if one can be found linked
    from the homepage -- that's usually where a fund's stated sector focus actually lives."""
    try:
        soup, final_url = _fetch_soup(url)
    except Exception:  # noqa: BLE001
        return None

    about_url = _find_about_link(soup, final_url)
    homepage_text = _visible_text(soup)

    about_text = ""
    if about_url and about_url.rstrip("/") != final_url.rstrip("/"):
        try:
            about_soup, _ = _fetch_soup(about_url)
            about_text = _visible_text(about_soup)
        except Exception:  # noqa: BLE001
            pass

    combined = f"{homepage_text[:4000]} {about_text[:4000]}".strip()
    return combined[:8000] or None


def _extract_sectors(company_name: str, page_text: str, api_key: str) -> list[str]:
    from openai import OpenAI

    if not INDUSTRY_TAXONOMY:
        return []

    taxonomy_list = "\n".join(f"- {name}" for name in INDUSTRY_TAXONOMY)
    prompt = (
        "You are helping a VC analyst tag a fund by its investment focus.\n"
        f"Company / fund name: {company_name}\n"
        f"Text scraped from their website (homepage and, where linked, their About/Focus page):\n{page_text}\n\n"
        "Funds usually describe this under headings like \"Focus Areas\", \"Investment Thesis\", "
        "\"What We Invest In\", or \"Portfolio\" -- look for that kind of language.\n\n"
        "Choose up to 5 industries from the list below that this company INVESTS IN or "
        "funds — its portfolio focus, not what kind of firm it is. Do NOT pick "
        "\"venture capital & private equity\" to describe the firm itself unless it "
        "specifically invests in other investment firms/funds.\n\n"
        "Allowed industries (choose ONLY from this list, copying the spelling exactly):\n"
        f"{taxonomy_list}\n\n"
        "Respond with ONLY a valid JSON array of strings, most relevant first, each one an "
        "exact match from the list above. If nothing on the page indicates a specific "
        "sector focus, respond with []."
    )
    try:
        from engine.openai_keys import call_with_failover, resolve_openai_keys

        response = call_with_failover(
            resolve_openai_keys(api_key),
            lambda key: OpenAI(api_key=key).responses.create(model=MODEL, input=prompt, max_output_tokens=200),
        )
        text = (getattr(response, "output_text", "") or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(data, list):
        return []

    valid = {name.lower(): name for name in INDUSTRY_TAXONOMY}
    matched: list[str] = []
    for item in data:
        canonical = valid.get(str(item).strip().lower())
        if canonical and canonical not in matched:
            matched.append(canonical)
    return matched[:5]


def detect_company_sectors(
    company_name: str,
    serper_api_key: str | None,
    serp_api_key: str | None,
    tavily_api_key: str | None,
    openai_api_key: str | None,
) -> SectorDetectionResult:
    """Best-effort, always returns a plain-language `error` instead of raising."""
    if not company_name or not company_name.strip():
        return SectorDetectionResult(None, [], "Please enter a company or fund name first.")
    if not openai_api_key:
        return SectorDetectionResult(None, [], "Sector detection isn't available right now.")

    website = find_official_website(company_name, serper_api_key, serp_api_key, tavily_api_key)
    if not website:
        return SectorDetectionResult(None, [], "We couldn't find their website. Please choose a sector from the list.")

    page_text = _fetch_company_text(website)
    if not page_text:
        return SectorDetectionResult(website, [], "We found their website but couldn't read it. Please choose a sector from the list.")

    sectors = _extract_sectors(company_name, page_text, openai_api_key)
    if not sectors:
        return SectorDetectionResult(website, [], "We couldn't tell which sector they focus on. Please choose a sector from the list.")

    return SectorDetectionResult(website, sectors, None)
