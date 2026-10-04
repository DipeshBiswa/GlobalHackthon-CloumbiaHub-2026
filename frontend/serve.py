"""Optional separate local frontend server with same-origin API proxy."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def handle_request(self):
        if not self.path.startswith("/api/"):
            return super().do_GET()
        size = int(self.headers.get("Content-Length", 0))
        headers = {k: v for k, v in self.headers.items() if k.lower() in {"content-type", "cookie"}}
        req = Request("http://127.0.0.1:8000" + self.path, data=self.rfile.read(size) if size else None, headers=headers, method=self.command)
        try:
            upstream = urlopen(req, timeout=180)
        except HTTPError as error:
            upstream = error
        with upstream:
            self.send_response(upstream.status)
            for key in ["Content-Type", "Set-Cookie"]:
                for value in upstream.headers.get_all(key, []):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(upstream.read())

    do_GET = do_POST = do_PATCH = do_DELETE = handle_request

if __name__ == "__main__":
    print("Echo frontend: http://127.0.0.1:5500")
    ThreadingHTTPServer(("127.0.0.1", 5500), Handler).serve_forever()
