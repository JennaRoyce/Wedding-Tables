#!/usr/bin/env python3

"""Simple local server for the seating app with repo-backed layout persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LAYOUT_PATH = ROOT / "data" / "seating-layout.json"


def read_layout() -> dict:
    if not LAYOUT_PATH.exists():
        return {"assignments": {}, "updated_at": None}

    try:
        payload = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"assignments": {}, "updated_at": None}

    if not isinstance(payload, dict):
        return {"assignments": {}, "updated_at": None}

    assignments = payload.get("assignments", {})
    if not isinstance(assignments, dict):
        assignments = {}

    return {
        "assignments": assignments,
        "updated_at": payload.get("updated_at"),
    }


def write_layout(assignments: dict) -> dict:
    payload = {
        "assignments": assignments,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    LAYOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


class SeatingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/layout":
            self._send_json(read_layout())
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/layout":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
            return

        assignments = payload.get("assignments", {})
        if not isinstance(assignments, dict):
            self.send_error(HTTPStatus.BAD_REQUEST, "assignments must be an object")
            return

        saved = write_layout(assignments)
        self._send_json(saved, status=HTTPStatus.OK)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), SeatingHandler)
    print("Serving seating app on http://127.0.0.1:8000")
    print(f"Persisting layout to {LAYOUT_PATH}")
    try:
      server.serve_forever()
    except KeyboardInterrupt:
      print("\nServer stopped.")
    finally:
      server.server_close()


if __name__ == "__main__":
    main()
