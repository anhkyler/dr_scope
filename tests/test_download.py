import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common.download import DownloadError, download_file, fetch_json, fetch_pages  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    calls: dict = {}

    def log_message(self, *args):  # keep test output quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        n = self.calls[self.path] = self.calls.get(self.path, 0) + 1
        if self.path == "/file.csv":
            self._send(200, b"id,amount\n1,10\n", "text/csv")
        elif self.path == "/flaky":
            self._send(503, {"err": "busy"}) if n == 1 else self._send(200, {"ok": True})
        elif self.path == "/missing":
            self._send(404, {"err": "nope"})
        else:
            self._send(200, {"path": self.path})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        page = body["page"]
        self._send(200, {"results": [page], "page_metadata": {"page": page, "hasNext": page < 3}})


@pytest.fixture(scope="module")
def base_url():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_download_file_writes_dest(base_url, tmp_path):
    dest = download_file(f"{base_url}/file.csv", tmp_path / "raw" / "file.csv")
    assert dest.read_text() == "id,amount\n1,10\n"


def test_download_file_no_overwrite(base_url, tmp_path):
    dest = tmp_path / "file.csv"
    dest.write_text("old")
    download_file(f"{base_url}/file.csv", dest, overwrite=False)
    assert dest.read_text() == "old"


def test_fetch_json_retries_on_503(base_url):
    assert fetch_json(f"{base_url}/flaky", backoff=0) == {"ok": True}


def test_fetch_json_raises_on_404(base_url):
    with pytest.raises(DownloadError, match="HTTP 404"):
        fetch_json(f"{base_url}/missing", backoff=0)


def test_fetch_json_query_params(base_url):
    assert fetch_json(f"{base_url}/q", params={"a": 1}) == {"path": "/q?a=1"}


def test_fetch_pages_follows_has_next(base_url):
    pages = list(fetch_pages(f"{base_url}/search", json_body={"limit": 1}))
    assert [p["results"][0] for p in pages] == [1, 2, 3]


def test_fetch_pages_max_pages(base_url):
    assert len(list(fetch_pages(f"{base_url}/search", json_body={}, max_pages=2))) == 2
