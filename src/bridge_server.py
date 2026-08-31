"""Local HTTP bridge so a remotely-hosted n8n instance can trigger this repo's
Python brief-generation code over a tunnel (e.g. cloudflared/ngrok), since a
managed/shared n8n instance has no filesystem access to this machine and no
Execute Command node.

Endpoints (both require header `X-Bridge-Token: <BRIDGE_TOKEN>`):
  GET /sectors            -> JSON list of unique sectors
  GET /brief?sector=<name> -> JSON {"brief": "<markdown>"}; also writes the
                              timestamped .md file to outputs/briefs/, same
                              as calling src.generate_brief_for_sector directly.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.config import ROOT_DIR
from src.generate_brief_for_sector import generate_brief_for_sector
from src.list_sectors import list_sectors

BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8000"))

if not BRIDGE_TOKEN:
    raise SystemExit(
        "BRIDGE_TOKEN is not set. Add BRIDGE_TOKEN=<a random string> to "
        f"{ROOT_DIR / '.env'} before starting the bridge server."
    )


class BridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        return self.headers.get("X-Bridge-Token") == BRIDGE_TOKEN

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        if not self._authorized():
            self._send_json(401, {"error": "missing or invalid X-Bridge-Token header"})
            return

        parsed = urlparse(self.path)

        if parsed.path == "/sectors":
            self._send_json(200, {"sectors": list_sectors()})
            return

        if parsed.path == "/brief":
            sector = parse_qs(parsed.query).get("sector", [None])[0]
            if not sector:
                self._send_json(400, {"error": "missing 'sector' query parameter"})
                return
            try:
                brief = generate_brief_for_sector(sector)
            except ValueError as exc:
                self._send_json(404, {"error": str(exc)})
                return
            self._send_json(200, {"brief": brief})
            return

        self._send_json(404, {"error": f"no such endpoint: {parsed.path}"})

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[bridge] {self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", BRIDGE_PORT), BridgeHandler)
    print(f"Bridge server listening on http://127.0.0.1:{BRIDGE_PORT}")
    print("Expose it publicly with, e.g.: cloudflared tunnel --url http://127.0.0.1:" + str(BRIDGE_PORT))
    server.serve_forever()


if __name__ == "__main__":
    main()
