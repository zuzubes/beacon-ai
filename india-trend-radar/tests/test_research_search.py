"""Tests for engine/research_search.py's find_official_website helper."""

from engine import research_search


def test_find_official_website_prefers_serper(monkeypatch):
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [{"link": "https://serper.example.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key")
    assert url == "https://serper.example.com"


def test_find_official_website_falls_back_to_serpapi_when_serper_fails(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("serper down")

    monkeypatch.setattr(research_search, "_serper_request", _boom)
    monkeypatch.setattr(
        research_search, "_serpapi_request",
        lambda *a, **k: {"organic_results": [{"link": "https://serpapi.example.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", None)
    assert url == "https://serpapi.example.com"


def test_find_official_website_falls_back_to_tavily_last(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(research_search, "_serper_request", _boom)
    monkeypatch.setattr(research_search, "_serpapi_request", _boom)
    monkeypatch.setattr(
        research_search, "_tavily_request",
        lambda *a, **k: {"results": [{"url": "https://tavily.example.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key")
    assert url == "https://tavily.example.com"


def test_find_official_website_returns_none_when_all_providers_fail(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(research_search, "_serper_request", _boom)
    monkeypatch.setattr(research_search, "_serpapi_request", _boom)
    monkeypatch.setattr(research_search, "_tavily_request", _boom)
    assert research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key") is None


def test_find_official_website_returns_none_without_any_keys():
    assert research_search.find_official_website("Acme", None, None, None) is None


def test_find_official_website_skips_providers_with_no_key(monkeypatch):
    monkeypatch.setattr(
        research_search, "_serpapi_request",
        lambda *a, **k: {"organic_results": [{"link": "https://serpapi.example.com"}]},
    )
    url = research_search.find_official_website("Acme", None, "serp-key", None)
    assert url == "https://serpapi.example.com"


def test_find_official_website_returns_none_on_empty_results(monkeypatch):
    monkeypatch.setattr(research_search, "_serper_request", lambda *a, **k: {"organic": []})
    assert research_search.find_official_website("Acme", "serper-key", None, None) is None
