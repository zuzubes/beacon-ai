"""Tests for engine/company_sectors.py -- company website -> industry/sector detection."""

import json

from engine import company_sectors


def test_industry_taxonomy_loads_from_data_file():
    assert len(company_sectors.INDUSTRY_TAXONOMY) == 147
    assert "venture capital & private equity" in company_sectors.INDUSTRY_TAXONOMY
    assert "information technology and services" in company_sectors.INDUSTRY_TAXONOMY


def test_extract_sectors_keeps_only_exact_taxonomy_matches(fake_openai):
    fake_openai(json.dumps(["financial services", "venture capital & private equity", "not a real sector"]))
    result = company_sectors._extract_sectors("Acme", "homepage text", "fake-key")
    assert result == ["financial services", "venture capital & private equity"]


def test_extract_sectors_is_case_insensitive_and_dedupes(fake_openai):
    fake_openai(json.dumps(["Financial Services", "financial services", "FINANCIAL SERVICES"]))
    result = company_sectors._extract_sectors("Acme", "homepage text", "fake-key")
    assert result == ["financial services"]


def test_extract_sectors_caps_at_five(fake_openai):
    six_valid = company_sectors.INDUSTRY_TAXONOMY[:6]
    fake_openai(json.dumps(six_valid))
    result = company_sectors._extract_sectors("Acme", "homepage text", "fake-key")
    assert result == six_valid[:5]


def test_extract_sectors_handles_malformed_json(fake_openai):
    fake_openai("not valid json")
    assert company_sectors._extract_sectors("Acme", "homepage text", "fake-key") == []


def test_extract_sectors_handles_non_list_json(fake_openai):
    fake_openai(json.dumps({"not": "a list"}))
    assert company_sectors._extract_sectors("Acme", "homepage text", "fake-key") == []


def test_extract_sectors_strips_markdown_fences(fake_openai):
    fake_openai("```json\n" + json.dumps(["financial services"]) + "\n```")
    assert company_sectors._extract_sectors("Acme", "homepage text", "fake-key") == ["financial services"]


def test_extract_sectors_returns_empty_without_a_taxonomy(fake_openai, monkeypatch):
    monkeypatch.setattr(company_sectors, "INDUSTRY_TAXONOMY", [])
    fake_openai(json.dumps(["financial services"]))
    assert company_sectors._extract_sectors("Acme", "homepage text", "fake-key") == []


def test_find_about_link_matches_hint_words():
    from bs4 import BeautifulSoup

    html = '<a href="/about-us">About Us</a><a href="/blog">Blog</a>'
    soup = BeautifulSoup(html, "html.parser")
    link = company_sectors._find_about_link(soup, "https://example.com")
    assert link == "https://example.com/about-us"


def test_find_about_link_returns_none_when_no_match():
    from bs4 import BeautifulSoup

    html = '<a href="/blog">Blog</a><a href="/contact">Contact</a>'
    soup = BeautifulSoup(html, "html.parser")
    assert company_sectors._find_about_link(soup, "https://example.com") is None


def test_visible_text_strips_script_style_nav_footer():
    from bs4 import BeautifulSoup

    html = (
        "<html><body>"
        "<nav>Nav links</nav>"
        "<script>var x = 1;</script>"
        "<style>.a{color:red}</style>"
        "<p>Real content here</p>"
        "<footer>Footer text</footer>"
        "</body></html>"
    )
    soup = BeautifulSoup(html, "html.parser")
    assert company_sectors._visible_text(soup) == "Real content here"


def test_detect_company_sectors_requires_company_name():
    result = company_sectors.detect_company_sectors("   ", "s", "sa", "t", "o")
    assert result.sectors == []
    assert result.error == "Please enter a company or fund name first."


def test_detect_company_sectors_requires_openai_key():
    result = company_sectors.detect_company_sectors("Acme", "s", "sa", "t", None)
    assert result.error == "Sector detection isn't available right now."


def test_detect_company_sectors_no_website_found(monkeypatch):
    monkeypatch.setattr(company_sectors, "find_official_website", lambda *a, **k: None)
    result = company_sectors.detect_company_sectors("Acme", None, None, None, "key")
    assert result.website is None
    assert result.error == "We couldn't find their website. Please choose a sector from the list."


def test_detect_company_sectors_unreadable_website(monkeypatch):
    monkeypatch.setattr(company_sectors, "find_official_website", lambda *a, **k: "https://acme.com")
    monkeypatch.setattr(company_sectors, "_fetch_company_text", lambda *a, **k: None)
    result = company_sectors.detect_company_sectors("Acme", None, None, None, "key")
    assert result.website == "https://acme.com"
    assert result.error == "We found their website but couldn't read it. Please choose a sector from the list."


def test_detect_company_sectors_no_signal(monkeypatch):
    monkeypatch.setattr(company_sectors, "find_official_website", lambda *a, **k: "https://acme.com")
    monkeypatch.setattr(company_sectors, "_fetch_company_text", lambda *a, **k: "some text")
    monkeypatch.setattr(company_sectors, "_extract_sectors", lambda *a, **k: [])
    result = company_sectors.detect_company_sectors("Acme", None, None, None, "key")
    assert result.error == "We couldn't tell which sector they focus on. Please choose a sector from the list."


def test_detect_company_sectors_success(monkeypatch):
    monkeypatch.setattr(company_sectors, "find_official_website", lambda *a, **k: "https://acme.com")
    monkeypatch.setattr(company_sectors, "_fetch_company_text", lambda *a, **k: "some text")
    monkeypatch.setattr(company_sectors, "_extract_sectors", lambda *a, **k: ["financial services"])
    result = company_sectors.detect_company_sectors("Acme", None, None, None, "key")
    assert (result.website, result.sectors, result.error) == ("https://acme.com", ["financial services"], None)
