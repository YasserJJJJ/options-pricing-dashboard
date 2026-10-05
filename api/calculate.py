"""Vercel Python function: POST /api/calculate."""
import json
from http.server import BaseHTTPRequestHandler
from dashboard import calculate_dashboard


class handler(BaseHTTPRequestHandler):
    def respond(self, status, data):
        body = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.respond(200, {"status": "ok", "service": "options-pricing"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 8192:
                return self.respond(400, {"error": "Request body must be between 1 and 8192 bytes."})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.respond(415, {"error": "Use Content-Type: application/json."})
            data = json.loads(self.rfile.read(length))
            self.respond(200, calculate_dashboard(data))
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError) as error:
            self.respond(400, {"error": str(error)})
