"""Vercel entrypoint for Beacon AI.

This thin wrapper keeps the actual landing-page implementation in
`india-trend-radar/app.py`, while exposing a root-level `app` variable so
Vercel detects the Python entrypoint reliably.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_APP_PATH = Path(__file__).resolve().parent / "india-trend-radar" / "app.py"
_SPEC = importlib.util.spec_from_file_location("beacon_ai_vercel_app", _APP_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import-time guard
    raise RuntimeError(f"Unable to load Vercel app entrypoint from {_APP_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

app = _MODULE.app
application = _MODULE.application
handler = _MODULE.handler

__all__ = ["app", "application", "handler"]
