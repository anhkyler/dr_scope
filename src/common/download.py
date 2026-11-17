"""Common download helpers (stdlib only – runs locally, on CI and on serverless).

Usage:
    from common.download import download_file, fetch_json, fetch_pages

    # Save a file into a Unity Catalog volume (or any local path)
    download_file("https://example.com/data.csv",
                  "/Volumes/workspace/demo/raw/data.csv")

    # Call a JSON API (GET or POST)
    data = fetch_json("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                      json_body={...})

    # Iterate over every page of a paginated JSON API
    for page in fetch_pages(url, json_body={..., "limit": 100}):
        rows = page["results"]
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
USER_AGENT = "databricks-learner-downloader/1.0"
_CHUNK = 1024 * 1024


class DownloadError(RuntimeError):
    """Raised when a request fails after all retries."""


def _build_request(
    url: str,
    method: str | None,
    params: Mapping[str, Any] | None,
    json_body: Any,
    headers: Mapping[str, str] | None,
) -> Request:
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urlencode(params, doseq=True)}"
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    method = (method or ("POST" if data is not None else "GET")).upper()
    return Request(url, data=data, headers=hdrs, method=method)


def _open_with_retry(req: Request, timeout: float, retries: int, backoff: float):
    """Open `req`, retrying transient errors with exponential backoff."""
    attempt = 0
    while True:
        try:
            return urlopen(req, timeout=timeout)
        except HTTPError as e:
            if e.code not in RETRYABLE_STATUS or attempt >= retries:
                body = e.read()[:500].decode("utf-8", "replace")
                raise DownloadError(f"{req.method} {req.full_url} -> HTTP {e.code}: {body}") from e
            wait = _retry_after(e) or backoff**attempt
        except (URLError, TimeoutError, ConnectionError) as e:
            if attempt >= retries:
                raise DownloadError(f"{req.method} {req.full_url} failed: {e}") from e
            wait = backoff**attempt
        attempt += 1
        log.warning("Retry %d/%d for %s in %.1fs", attempt, retries, req.full_url, wait)
        time.sleep(wait)


def _retry_after(e: HTTPError) -> float | None:
    value = e.headers.get("Retry-After") if e.headers else None
    try:
        return float(value) if value else None
    except ValueError:
        return None


def download_file(
    url: str,
    dest: str | os.PathLike,
    *,
    method: str | None = None,
    params: Mapping[str, Any] | None = None,
    json_body: Any = None,
    headers: Mapping[str, str] | None = None,
    overwrite: bool = True,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
) -> Path:
    """Stream `url` to `dest` and return the destination path.

    The body is streamed to a local temp file first, then moved into place, so a
    failed download never leaves a half-written file at `dest`. This also works
    for `/Volumes/...` paths, which only support sequential writes.
    """
    dest = Path(dest)
    if dest.exists() and not overwrite:
        log.info("Skip download, %s already exists", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    req = _build_request(url, method, params, json_body, headers)
    fd, tmp = tempfile.mkstemp(prefix="dl_", suffix=dest.suffix)
    try:
        with _open_with_retry(req, timeout, retries, backoff) as resp, os.fdopen(fd, "wb") as out:
            shutil.copyfileobj(resp, out, _CHUNK)
        shutil.move(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    log.info("Downloaded %s -> %s (%d bytes)", url, dest, dest.stat().st_size)
    return dest


def fetch_json(
    url: str,
    *,
    method: str | None = None,
    params: Mapping[str, Any] | None = None,
    json_body: Any = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
) -> Any:
    """Call a JSON API and return the parsed response. POST is used if `json_body` is given."""
    hdrs = {"Accept": "application/json", **(headers or {})}
    req = _build_request(url, method, params, json_body, hdrs)
    with _open_with_retry(req, timeout, retries, backoff) as resp:
        return json.load(resp)


def _usaspending_has_next(page: Mapping[str, Any]) -> bool:
    return bool(page.get("page_metadata", {}).get("hasNext"))


def fetch_pages(
    url: str,
    *,
    json_body: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
    page_field: str = "page",
    start_page: int = 1,
    max_pages: int | None = None,
    has_next: Callable[[Mapping[str, Any]], bool] = _usaspending_has_next,
    **kwargs: Any,
) -> Iterator[Any]:
    """Yield each page of a page-numbered JSON API.

    The page number goes into the JSON body (POST APIs) or, when there is no
    body, into the query string. `has_next(page)` decides whether to continue;
    the default reads `page_metadata.hasNext` (USAspending format).
    """
    page_no = start_page
    fetched = 0
    while max_pages is None or fetched < max_pages:
        if json_body is not None:
            page = fetch_json(url, json_body={**json_body, page_field: page_no}, params=params, **kwargs)
        else:
            page = fetch_json(url, params={**(params or {}), page_field: page_no}, **kwargs)
        yield page
        fetched += 1
        if not has_next(page):
            return
        page_no += 1
