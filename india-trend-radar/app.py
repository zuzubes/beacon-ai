"""Vercel entrypoint for Beacon AI.

This file exports a minimal WSGI `app` so Vercel can deploy the repository
without trying to treat the Streamlit UI as a Python function entrypoint.
Run the full product locally with `streamlit run streamlit_app.py`.
"""

from __future__ import annotations

from textwrap import dedent


def _wsgi_app(environ, start_response):  # noqa: ANN001
    body = dedent(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Beacon AI</title>
          <style>
            body {
              margin: 0;
              min-height: 100vh;
              display: grid;
              place-items: center;
              background: linear-gradient(180deg, #eef3f8 0%, #f5f7fb 100%);
              color: #0f172a;
              font-family: Arial, Helvetica, sans-serif;
            }
            .card {
              max-width: 720px;
              margin: 24px;
              padding: 32px;
              border-radius: 20px;
              background: white;
              box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
              border: 1px solid #d8e1ea;
            }
            h1 {
              margin: 0 0 12px;
              font-size: 2rem;
              line-height: 1.1;
            }
            p {
              margin: 0 0 12px;
              color: #475569;
              line-height: 1.55;
            }
            a {
              color: #1d4ed8;
              text-decoration: none;
            }
            .hint {
              font-size: 0.92rem;
              color: #64748b;
            }
          </style>
        </head>
        <body>
          <div class="card">
            <h1>Beacon AI</h1>
            <p>This deployment exposes a lightweight Vercel landing page.</p>
            <p>Run the full Streamlit product locally from <code>india-trend-radar/streamlit_app.py</code>.</p>
            <p class="hint">If you want the interactive app on the web, deploy the Streamlit UI separately on a host that supports Streamlit.</p>
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
