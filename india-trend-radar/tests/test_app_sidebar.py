"""Tests for app.py's sidebar: the Detect Industry button and the Industry/Sector dropdown.

Uses Streamlit's own AppTest harness (streamlit.testing.v1) to drive the real script instead
of hand-rolling a fake Streamlit environment.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from engine import company_sectors, news, trend_analysis, trends
from engine.company_sectors import SectorDetectionResult

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"

DEFAULT_INDUSTRY_LABELS = [
    "Apparel & Fashion",
    "Beauty & Cosmetics",
    "Consumer Electronics",
    "Ecology & Environment",
    "Entertainment",
    "Farms & Ranches",
    "Food & Beverages",
    "Information Technology",
    "Jewelry & Luxury Products",
    "Sporting Goods",
    "Wellness",
    "Wine & Spirits",
]


def _run_app() -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    return at


def test_default_industry_dropdown_has_twelve_built_in_options():
    at = _run_app()
    sel = at.sidebar.selectbox(key="industry_select")
    assert sel.options == DEFAULT_INDUSTRY_LABELS
    assert sel.value == "apparel_and_fashion"


def test_detect_industry_with_empty_company_shows_plain_language_warning():
    at = _run_app()
    at.sidebar.button[0].click().run()  # "Detect Industry from Website", company left blank
    assert [w.value for w in at.sidebar.warning] == ["Please enter a company or fund name first."]
    sel = at.sidebar.selectbox(key="industry_select")
    assert sel.options == DEFAULT_INDUSTRY_LABELS


def test_detect_industry_error_shows_plain_language_warning_and_leaves_dropdown_unchanged(monkeypatch):
    monkeypatch.setattr(
        company_sectors,
        "detect_company_sectors",
        lambda *a, **k: SectorDetectionResult(
            None, [], "We couldn't find their website. Please choose a sector from the list."
        ),
    )
    at = _run_app()
    at.sidebar.text_input[0].input("Acme").run()
    at.sidebar.button[0].click().run()
    assert [w.value for w in at.sidebar.warning] == [
        "We couldn't find their website. Please choose a sector from the list."
    ]
    sel = at.sidebar.selectbox(key="industry_select")
    assert sel.options == DEFAULT_INDUSTRY_LABELS
    assert sel.value == "apparel_and_fashion"


def test_detect_industry_new_sector_is_prepended_and_auto_selected(monkeypatch):
    monkeypatch.setattr(
        company_sectors,
        "detect_company_sectors",
        lambda *a, **k: SectorDetectionResult("https://acme.com", ["financial services"], None),
    )
    at = _run_app()
    at.sidebar.text_input[0].input("Acme").run()
    at.sidebar.button[0].click().run()
    assert [w.value for w in at.sidebar.success] == ["Detected sector: Financial Services"]
    sel = at.sidebar.selectbox(key="industry_select")
    assert sel.options[0] == "Financial Services"
    assert sel.options[1:] == DEFAULT_INDUSTRY_LABELS
    assert sel.value == "financial_services"


def test_detect_industry_existing_sector_is_not_duplicated(monkeypatch):
    monkeypatch.setattr(
        company_sectors,
        "detect_company_sectors",
        lambda *a, **k: SectorDetectionResult("https://acme.com", ["consumer electronics"], None),
    )
    at = _run_app()
    at.sidebar.text_input[0].input("Acme").run()
    at.sidebar.button[0].click().run()
    sel = at.sidebar.selectbox(key="industry_select")
    assert sel.options == DEFAULT_INDUSTRY_LABELS  # no duplicate entry added
    assert sel.value == "consumer_electronics"  # but the existing option still gets selected


def test_run_analysis_does_not_pass_company_to_trend_generation(monkeypatch):
    captured = {}
    real_generate_mock_trends = trends.generate_mock_trends

    def fake_generate_mock_trends(time_range, region, industry, *a, **k):
        # Delegate to the real generator (rather than returning e.g. []) so downstream
        # rendering -- which expects a realistic, non-empty trend hierarchy -- still works;
        # only the call arguments are what this test actually cares about.
        captured["trends_args"] = (time_range, region, industry)
        return real_generate_mock_trends(time_range, region, industry, *a, **k)

    def fake_generate_mock_news(company, time_range, region, industry):
        return []

    monkeypatch.setattr(trends, "generate_mock_trends", fake_generate_mock_trends)
    monkeypatch.setattr(news, "generate_mock_news", fake_generate_mock_news)
    monkeypatch.setattr(trend_analysis, "build_trend_analysis_report", lambda *a, **k: None)
    # app.py's own _load_env_file() re-reads the real .env on every fresh script execution and
    # only skips a key that's *already present* in os.environ -- so these must be set to an
    # empty string (falsy, but present) rather than deleted, or the real key just gets reloaded
    # from disk and this test would fire a live, unmocked network/OpenAI call.
    for var in ("OPENAI_API_KEY", "openai_api_key", "NEWSAPI_KEY", "NEWS_API_KEY"):
        monkeypatch.setenv(var, "")

    at = _run_app()
    at.sidebar.text_input[0].input("Acme").run()
    at.sidebar.button[1].click().run()  # "Run Analysis"

    assert not at.exception
    assert captured["trends_args"] == ("Past 1 week", "US & China (Both)", "apparel_and_fashion")
