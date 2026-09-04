"""Shared OpenAI API key resolution and automatic failover for Beacon AI.

Every engine module that calls the OpenAI API resolves its key list via
`resolve_openai_keys()` and wraps the actual call in `call_with_failover()`
instead of calling `OpenAI(api_key=...)` with a single key directly. That way,
if a key hits a rate limit or has run out of quota, the same call is retried
against each backup key in turn (OPENAI_API_KEY_2, then OPENAI_API_KEY_3) with
no user-visible failure -- any other kind of error (bad request, network
issue, etc.) is not retried, since a different key wouldn't fix it.
"""

from __future__ import annotations

import os
from typing import Callable, TypeVar

T = TypeVar("T")


def resolve_openai_keys(primary: str | None = None) -> list[str]:
    """Ordered keys to try: `primary` (or OPENAI_API_KEY from the environment)
    first, then OPENAI_API_KEY_2 and OPENAI_API_KEY_3, each only if set and not
    already in the list."""
    keys: list[str] = []
    first = (primary or os.getenv("OPENAI_API_KEY", "")).strip()
    if first:
        keys.append(first)
    for env_name in ("OPENAI_API_KEY_2", "OPENAI_API_KEY_3"):
        key = os.getenv(env_name, "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    from openai import RateLimitError

    if isinstance(exc, RateLimitError):
        return True
    # Fall back to a text match in case a differently-shaped error (e.g. raised by
    # code that already re-wrapped the original exception) still carries the signal.
    message = str(exc).lower()
    return "insufficient_quota" in message or "rate_limit" in message or "rate limit" in message


def call_with_failover(keys: list[str], build_and_call: Callable[[str], T]) -> T:
    """Calls `build_and_call(api_key)` for each key in order. Moves on to the next
    key only when the call fails with a rate-limit/quota error; any other exception,
    or exhausting every key, propagates to the caller."""
    if not keys:
        raise RuntimeError("No OpenAI API key configured")
    for index, key in enumerate(keys):
        try:
            return build_and_call(key)
        except Exception as exc:  # noqa: BLE001
            is_last_key = index == len(keys) - 1
            if is_last_key or not _is_quota_or_rate_limit_error(exc):
                raise
    raise AssertionError("unreachable")  # pragma: no cover
