"""Tests for engine/growth_companies.py -- growing-companies and social-signal lookups
for the Sub-Trend Drill-Down tab."""

import json

import pytest

from engine import growth_companies


def test_generate_mock_companies_is_deterministic():
    first = growth_companies.generate_mock_companies("AI Copilots for SMBs", "Information Technology", "United States")
    second = growth_companies.generate_mock_companies("AI Copilots for SMBs", "Information Technology", "United States")
    assert first == second


def test_generate_mock_companies_varies_by_sub_trend():
    a = growth_companies.generate_mock_companies("AI Copilots for SMBs", "Information Technology", "United States")
    b = growth_companies.generate_mock_companies("Grid-Scale Storage", "Energy", "United States")
    assert a != b


def test_generate_mock_companies_returns_requested_count_all_marked_sample():
    companies = growth_companies.generate_mock_companies("Sub", "Industry", "Region", count=5)
    assert len(companies) == 5
    assert all(c["is_sample"] for c in companies)
    assert all(c["name"].endswith("(sample)") for c in companies)


def test_generate_mock_social_signals_is_deterministic_and_marked_sample():
    first = growth_companies.generate_mock_social_signals("AI Copilots", "IT", "United States")
    second = growth_companies.generate_mock_social_signals("AI Copilots", "IT", "United States")
    assert first == second
    assert first["is_sample"] is True
    assert len(first["tiktok_hashtags"]) == 5
    assert len(first["instagram_hashtags"]) == 5
    assert len(first["reddit_signals"]) == 3


def test_call_live_companies_parses_and_normalizes(fake_openai):
    fake_openai(
        json.dumps(
            [
                {"name": "Acme AI", "growth_reason": "Landed a distribution deal.", "growth_pct": 120},
                {"name": "", "growth_reason": "Should be dropped -- no name."},
                {"name": "Beta Robotics", "growth_reason": "Expanding manufacturing."},
            ]
        )
    )
    result = growth_companies.call_live_companies("Sub", "Industry", "United States", "fake-key")
    assert [c["name"] for c in result] == ["Acme AI", "Beta Robotics"]
    assert result[0]["growth_pct"] == 120
    assert all(c["is_sample"] is False for c in result)


def test_call_live_companies_strips_markdown_fences(fake_openai):
    fake_openai("```json\n" + json.dumps([{"name": "Acme", "growth_reason": "x"}]) + "\n```")
    result = growth_companies.call_live_companies("Sub", "Industry", "Region", "fake-key")
    assert result[0]["name"] == "Acme"


def test_call_live_companies_raises_on_malformed_json(fake_openai):
    fake_openai("not valid json")
    with pytest.raises(RuntimeError):
        growth_companies.call_live_companies("Sub", "Industry", "Region", "fake-key")


def test_call_live_companies_raises_on_non_array_json(fake_openai):
    fake_openai(json.dumps({"not": "a list"}))
    with pytest.raises(ValueError):
        growth_companies.call_live_companies("Sub", "Industry", "Region", "fake-key")


def test_call_live_social_signals_parses_and_normalizes(fake_openai):
    fake_openai(
        json.dumps(
            {
                "tiktok_hashtags": ["#trend1", "#trend2"],
                "instagram_hashtags": ["#trend3"],
                "reddit_signals": [
                    {"title": "Post title", "subreddit": "r/startups", "why_relevant": "because"},
                    {"title": "", "subreddit": "r/x", "why_relevant": "dropped -- no title"},
                ],
            }
        )
    )
    result = growth_companies.call_live_social_signals("Sub", "Industry", "Region", "fake-key")
    assert result["tiktok_hashtags"] == ["#trend1", "#trend2"]
    assert result["instagram_hashtags"] == ["#trend3"]
    assert len(result["reddit_signals"]) == 1
    assert result["reddit_signals"][0]["title"] == "Post title"
    assert result["is_sample"] is False


def test_call_live_social_signals_raises_on_non_object_json(fake_openai):
    fake_openai(json.dumps(["not", "an", "object"]))
    with pytest.raises(ValueError):
        growth_companies.call_live_social_signals("Sub", "Industry", "Region", "fake-key")


def test_a_live_call_failure_falls_back_to_mock_in_app_pattern(fake_openai):
    """Mirrors how streamlit_app.py is expected to use this module: try the live call, fall back to
    mock on any exception, exactly like trends.py's call_live_trends / generate_mock_trends."""
    fake_openai("not valid json")
    try:
        companies = growth_companies.call_live_companies("Sub", "Industry", "Region", "fake-key")
    except Exception:  # noqa: BLE001
        companies = None
    if not companies:
        companies = growth_companies.generate_mock_companies("Sub", "Industry", "Region")
    assert companies
    assert all(c["is_sample"] for c in companies)
