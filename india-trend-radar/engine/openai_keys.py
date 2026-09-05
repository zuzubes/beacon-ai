"""Shared OpenAI API key resolution and automatic failover for Beacon AI.

Every engine module that calls the OpenAI API resolves its key list via
`resolve_openai_keys()` and wraps the actual call in `call_with_failover()`
instead of calling `OpenAI(api_key=...)` with a single key directly. That way,
if a key is rate limited, out of quota, over its spend cap, or has been rotated
out (revoked), the same call is retried against each remaining key in turn with
no user-visible failure.

Backup keys are discovered dynamically: any `OPENAI_API_KEY_<n>` in the
environment joins the rotation in numeric order, so adding OPENAI_API_KEY_4 to
`.env` needs no code change here.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

BACKUP_KEY_PATTERN = re.compile(r"^OPENAI_API_KEY_(\d+)$")

# HTTP statuses where a *different* key can plausibly succeed: 401 revoked/incorrect
# key, 403 project lacks access, 429 rate limited or over its spend cap. A 400 is a
# bad request -- it fails identically on every key, so it must not burn the keyring.
RETRYABLE_STATUS_CODES = frozenset({401, 403, 429})

RETRYABLE_MESSAGE_MARKERS = (
    "insufficient_quota",
    "rate_limit",
    "rate limit",
    "spend limit",
    "quota",
    "invalid_api_key",
    "incorrect api key",
    "expired",
    "revoked",
)


def resolve_openai_keys(primary: str | None = None) -> list[str]:
    """Ordered keys to try: `primary` first (when given), then OPENAI_API_KEY from
    the environment, then every OPENAI_API_KEY_<n> in ascending numeric order.
    Blanks are dropped and duplicates collapse to their first position."""
    candidates: list[str] = [primary or "", os.getenv("OPENAI_API_KEY", "")]

    numbered: list[tuple[int, str]] = []
    for name, value in os.environ.items():
        match = BACKUP_KEY_PATTERN.match(name)
        if match:
            numbered.append((int(match.group(1)), value))
    candidates.extend(value for _, value in sorted(numbered, key=lambda item: item[0]))

    keys: list[str] = []
    for candidate in candidates:
        key = (candidate or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _should_try_next_key(exc: Exception) -> bool:
    """True when the failure is key-specific, so another key may succeed."""
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code in RETRYABLE_STATUS_CODES

    try:  # pragma: no cover - exercised implicitly wherever the SDK is installed
        from openai import AuthenticationError, PermissionDeniedError, RateLimitError

        if isinstance(exc, (RateLimitError, AuthenticationError, PermissionDeniedError)):
            return True
    except Exception:  # noqa: BLE001
        pass

    # Fall back to a text match in case a differently-shaped error (e.g. raised by
    # code that already re-wrapped the original exception) still carries the signal.
    message = str(exc).lower()
    return any(marker in message for marker in RETRYABLE_MESSAGE_MARKERS)


def call_with_failover(keys: list[str], build_and_call: Callable[[str], T]) -> T:
    """Calls `build_and_call(api_key)` for each key in order. Moves on to the next key
    when the call fails in a way another key could fix (rate limit, quota, spend cap,
    revoked/incorrect key, permission denied); any other exception, or exhausting every
    key, propagates to the caller."""
    if not keys:
        raise RuntimeError("No OpenAI API key configured")
    for index, key in enumerate(keys):
        try:
            return build_and_call(key)
        except Exception as exc:  # noqa: BLE001
            is_last_key = index == len(keys) - 1
            if is_last_key or not _should_try_next_key(exc):
                logger.warning(
                    "openai call failed on key %d/%d (%s: %s); %s",
                    index + 1,
                    len(keys),
                    type(exc).__name__,
                    exc,
                    "no keys left to try" if is_last_key else "error is not key-specific, not rotating",
                )
                raise
            logger.warning(
                "openai key %d/%d failed (%s: %s); rotating to the next key",
                index + 1,
                len(keys),
                type(exc).__name__,
                exc,
            )
    raise AssertionError("unreachable")  # pragma: no cover
