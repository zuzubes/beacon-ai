"""Tests for engine/trends.py -- company/fund identity must not influence trend generation
(the trend hierarchy is driven by time_range/region/industry only)."""

import inspect
import json

from engine import trends


def test_generate_mock_trends_signature_has_no_company():
    params = list(inspect.signature(trends.generate_mock_trends).parameters)
    assert "company" not in params
    assert params[:3] == ["time_range", "region", "industry"]


def test_call_live_trends_signature_has_no_company():
    params = list(inspect.signature(trends.call_live_trends).parameters)
    assert "company" not in params
    assert params[:3] == ["time_range", "region", "industry"]


def test_live_prompt_template_has_no_company_placeholder():
    assert "{company}" not in trends.LIVE_PROMPT_TEMPLATE
    assert "Company" not in trends.LIVE_PROMPT_TEMPLATE


def test_generate_mock_trends_is_deterministic():
    first = trends.generate_mock_trends("Past 1 week", "US & China (Both)", "information_technology")
    second = trends.generate_mock_trends("Past 1 week", "US & China (Both)", "information_technology")
    assert first == second


def test_generate_mock_trends_varies_by_industry():
    a = trends.generate_mock_trends("Past 1 week", "United States", "wellness")
    b = trends.generate_mock_trends("Past 1 week", "United States", "consumer_electronics")
    assert a != b


def test_call_live_trends_prompt_excludes_company(monkeypatch):
    captured = {}

    class _FakeResponse:
        status = "completed"
        output_text = json.dumps([])

    class _FakeResponses:
        def create(self, **kwargs):
            captured["input"] = kwargs["input"]
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key=None):
            self.responses = _FakeResponses()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient)

    result = trends.call_live_trends("Past 1 week", "United States", "wellness", "fake-key")
    assert result == []
    assert "company" not in captured["input"].lower()
