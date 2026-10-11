"""Small local webhook receiver for demonstrating Alertmanager delivery."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length)
        try:
            alert = json.loads(payload)
        except json.JSONDecodeError:
            self.send_error(400, "Expected JSON")
            return
        print(json.dumps(alert, separators=(",", ":")), flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received")

    def log_message(self, format: str, *args: object) -> None:
        print("webhook " + (format % args), flush=True)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8081), AlertHandler).serve_forever()
