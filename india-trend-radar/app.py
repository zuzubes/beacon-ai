"""Vercel entrypoint for Beacon AI.

This file exports a minimal WSGI `app` so Vercel can deploy the repository
without trying to treat the Streamlit UI as a Python function entrypoint.
Run the full product locally with `streamlit run streamlit_app.py`.
"""

from __future__ import annotations

import base64
import html
import os
from textwrap import dedent

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
FAVICON_PATH = ROOT_DIR / "assets" / "beacon-ai-icon.png"


def _favicon_data_uri() -> str:
    if not FAVICON_PATH.exists():
        return ""
    data = FAVICON_PATH.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _wsgi_app(environ, start_response):  # noqa: ANN001
    streamlit_url = os.getenv("STREAMLIT_APP_URL", "").strip()
    favicon_uri = _favicon_data_uri()
    launch_link = (
        f'<a class="button button-primary" href="{html.escape(streamlit_url, quote=True)}" target="_blank" rel="noopener noreferrer">Open Streamlit app</a>'
        if streamlit_url
        else ""
    )
    launch_note = (
        '<p class="hint">Interactive analysis is available in the Streamlit deployment linked below.</p>'
        if streamlit_url
        else '<p class="hint">Set <code>STREAMLIT_APP_URL</code> to link this page to the interactive Streamlit deployment.</p>'
    )
    body = dedent(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Beacon AI</title>
          {f'<link rel="icon" type="image/png" href="{favicon_uri}">' if favicon_uri else ""}
          <style>
            :root {
              --navy: #0f172a;
              --slate: #475569;
              --line: #d8e1ea;
              --cream: #f6f7fb;
              --blue: #1d4ed8;
              --blue-soft: #eff6ff;
            }
            body {
              margin: 0;
              min-height: 100vh;
              background:
                radial-gradient(circle at top left, rgba(29, 78, 216, 0.08), transparent 32%),
                radial-gradient(circle at bottom right, rgba(15, 23, 42, 0.08), transparent 24%),
                linear-gradient(180deg, #eef3f8 0%, #f6f8fc 100%);
              color: var(--navy);
              font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }
            .page {
              min-height: 100vh;
              display: grid;
              place-items: center;
              padding: 32px 20px;
            }
            .card {
              width: min(900px, 100%);
              padding: 36px;
              border-radius: 28px;
              background: rgba(255,255,255,0.86);
              backdrop-filter: blur(14px);
              box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
              border: 1px solid rgba(216, 225, 234, 0.9);
            }
            h1 {
              margin: 0 0 12px;
              font-size: clamp(2.4rem, 4vw, 4rem);
              line-height: 0.98;
              letter-spacing: -0.05em;
            }
            p {
              margin: 0 0 14px;
              color: var(--slate);
              line-height: 1.55;
              font-size: 1.04rem;
            }
            .eyebrow {
              display: inline-flex;
              align-items: center;
              gap: 10px;
              padding: 7px 12px;
              border-radius: 999px;
              background: var(--blue-soft);
              color: var(--blue);
              font-size: 0.8rem;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              margin-bottom: 18px;
            }
            .grid {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 14px;
              margin-top: 26px;
            }
            .tile {
              border: 1px solid var(--line);
              border-radius: 20px;
              background: rgba(255,255,255,0.72);
              padding: 18px;
            }
            .tile h2 {
              margin: 0 0 8px;
              font-size: 0.88rem;
              text-transform: uppercase;
              letter-spacing: 0.12em;
              color: var(--slate);
            }
            .tile p {
              margin: 0;
              font-size: 0.98rem;
            }
            .actions {
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin-top: 26px;
              align-items: center;
            }
            a {
              color: var(--blue);
              text-decoration: none;
            }
            .button {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              min-height: 46px;
              padding: 0 18px;
              border-radius: 999px;
              font-weight: 700;
              border: 1px solid var(--line);
              background: white;
              color: var(--navy);
            }
            .button-primary {
              background: var(--navy);
              color: white;
              border-color: var(--navy);
            }
            .hint {
              font-size: 0.92rem;
              color: #64748b;
            }
          </style>
        </head>
        <body>
          <div class="page">
          <div class="card">
            <div class="eyebrow">Beacon AI</div>
            <h1>Beacon AI</h1>
            <p>Trend intelligence for macro, mega, and sub-trend research, with a Streamlit workspace for analysis and a lightweight Vercel surface for the public entry point.</p>
            <div class="grid">
              <div class="tile">
                <h2>Streamlit app</h2>
                <p>Run the full interactive experience locally with <code>streamlit run streamlit_app.py</code>.</p>
              </div>
              <div class="tile">
                <h2>Deployment model</h2>
                <p>Vercel hosts this landing page while the Streamlit UI can be deployed separately on a Streamlit-compatible host.</p>
              </div>
            </div>
            <div class="actions">
              {launch_link}
            </div>
            {launch_note}
          </div>
          </div>
        </body>
        </html>
        """
    ).strip().encode("utf-8")

    start_response(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


app = _wsgi_app
application = _wsgi_app
handler = _wsgi_app

__all__ = ["app", "application", "handler"]
