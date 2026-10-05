"""Local development server for the same static UI and API deployed on Vercel."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from api.calculate import handler


class LocalHandler(handler, SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "public"), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == "/api/calculate":
            return handler.do_GET(self)
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/calculate":
            return self.respond(404, {"error": "Endpoint not found."})
        return handler.do_POST(self)


if __name__ == "__main__":
    print("Options Pricing Dashboard: http://localhost:3000", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 3000), LocalHandler).serve_forever()
