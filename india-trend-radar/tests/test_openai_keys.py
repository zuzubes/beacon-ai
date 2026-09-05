"""Tests for engine/openai_keys.py -- key discovery and cross-key failover."""

import pytest

from engine import openai_keys


class _StatusError(Exception):
    """Stands in for an openai APIStatusError, which carries an HTTP status_code."""

    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"error {status_code}")
        self.status_code = status_code


def _clear_keys(monkeypatch):
    for name in list(dict(__import__("os").environ)):
        if name.startswith("OPENAI_API_KEY"):
            monkeypatch.delenv(name, raising=False)


def test_resolve_keys_prefers_explicit_primary(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "env-primary")
    assert openai_keys.resolve_openai_keys("explicit") == ["explicit", "env-primary"]


def test_resolve_keys_falls_back_to_environment_primary(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "env-primary")
    assert openai_keys.resolve_openai_keys(None) == ["env-primary"]


def test_resolve_keys_discovers_any_numbered_backup(monkeypatch):
    """Newly added backups (_4, _5, ...) must rotate without a code change."""
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "one")
    monkeypatch.setenv("OPENAI_API_KEY_2", "two")
    monkeypatch.setenv("OPENAI_API_KEY_5", "five")
    monkeypatch.setenv("OPENAI_API_KEY_10", "ten")
    assert openai_keys.resolve_openai_keys(None) == ["one", "two", "five", "ten"]


def test_resolve_keys_orders_backups_numerically_not_alphabetically(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY_10", "ten")
    monkeypatch.setenv("OPENAI_API_KEY_2", "two")
    assert openai_keys.resolve_openai_keys(None) == ["two", "ten"]


def test_resolve_keys_dedupes_and_skips_blanks(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "same")
    monkeypatch.setenv("OPENAI_API_KEY_2", "same")
    monkeypatch.setenv("OPENAI_API_KEY_3", "   ")
    monkeypatch.setenv("OPENAI_API_KEY_4", "other")
    assert openai_keys.resolve_openai_keys(None) == ["same", "other"]


def test_resolve_keys_ignores_non_numeric_suffixes(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "one")
    monkeypatch.setenv("OPENAI_API_KEY_BACKUP", "not-numbered")
    assert openai_keys.resolve_openai_keys(None) == ["one"]


def test_failover_returns_first_successful_key():
    assert openai_keys.call_with_failover(["a", "b"], lambda key: f"used-{key}") == "used-a"


def test_failover_rotates_past_a_rate_limited_key():
    tried = []

    def _call(key):
        tried.append(key)
        if key == "a":
            raise _StatusError(429, "rate_limit_exceeded")
        return "ok"

    assert openai_keys.call_with_failover(["a", "b"], _call) == "ok"
    assert tried == ["a", "b"]


def test_failover_rotates_past_a_spend_limited_key():
    """The exact failure seen in production: 429, 'enforced spend limit'."""
    tried = []

    def _call(key):
        tried.append(key)
        if key == "a":
            raise _StatusError(429, "Your project has reached its configured enforced spend limit")
        return "ok"

    assert openai_keys.call_with_failover(["a", "b"], _call) == "ok"
    assert tried == ["a", "b"]


def test_failover_rotates_past_a_revoked_key():
    """A rotated-out key returns 401 -- a different key fixes that, so try the next one."""
    tried = []

    def _call(key):
        tried.append(key)
        if key == "a":
            raise _StatusError(401, "Incorrect API key provided")
        return "ok"

    assert openai_keys.call_with_failover(["a", "b"], _call) == "ok"
    assert tried == ["a", "b"]


def test_failover_rotates_past_a_permission_denied_key():
    tried = []

    def _call(key):
        tried.append(key)
        if key == "a":
            raise _StatusError(403, "project does not have access to model")
        return "ok"

    assert openai_keys.call_with_failover(["a", "b"], _call) == "ok"
    assert tried == ["a", "b"]


def test_failover_does_not_rotate_on_a_bad_request():
    """A malformed prompt fails identically on every key -- don't burn the whole keyring."""
    tried = []

    def _call(key):
        tried.append(key)
        raise _StatusError(400, "invalid 'max_output_tokens'")

    with pytest.raises(_StatusError):
        openai_keys.call_with_failover(["a", "b"], _call)
    assert tried == ["a"]


def test_failover_raises_the_last_error_when_every_key_fails():
    def _call(key):
        raise _StatusError(429, f"rate_limit on {key}")

    with pytest.raises(_StatusError, match="rate_limit on c"):
        openai_keys.call_with_failover(["a", "b", "c"], _call)


def test_failover_without_any_key_is_a_clear_error():
    with pytest.raises(RuntimeError, match="No OpenAI API key"):
        openai_keys.call_with_failover([], lambda key: "never")
