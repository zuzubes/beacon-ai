"""Shared pytest fixtures for the Beacon AI test suite."""

import pytest


class _FakeResponse:
    def __init__(self, text):
        self.output_text = text
        self.status = "completed"


class _FakeResponses:
    def __init__(self, text):
        self._text = text

    def create(self, **kwargs):
        return _FakeResponse(self._text)


class _FakeOpenAIClient:
    def __init__(self, text):
        self.responses = _FakeResponses(text)


@pytest.fixture
def fake_openai(monkeypatch):
    """Patches openai.OpenAI so any `from openai import OpenAI; OpenAI(api_key=...)` call in
    the code under test returns a fake client whose `.responses.create(...)` yields a fixed
    `.output_text`. Call the fixture with the canned response text before exercising the code;
    call it again to change the response mid-test."""
    import openai

    def _set(text: str) -> None:
        monkeypatch.setattr(openai, "OpenAI", lambda api_key=None: _FakeOpenAIClient(text))

    return _set
