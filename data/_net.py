"""Shared HTTP layer for the ATHANOR corpus fetchers.

Design goals
------------
* polite: single-threaded, rate limited per host, stable descriptive User-Agent
* robust: bounded exponential backoff with jitter, retries on 5xx / timeouts
* resumable: every API response and every download is cached on disk, so a
  re-run after a crash only fetches what is missing
* idempotent: writing a file that already exists with the same content is a no-op

No credentials, no scrapers that hammer. Everything here is public-domain
material or a public open API.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
RAW = CORPUS / "raw"
REGISTRY = CORPUS / "registry"
PROCESSED = CORPUS / "processed"
CACHE = ROOT / "data" / ".cache"

USER_AGENT = (
    "ATHANOR-corpus-builder/1.0 (EthnoHack 2026 research corpus; "
    "contact: athanor-corpus@example.org) requests/{}".format(requests.__version__)
)

# Per-host minimum spacing, seconds. Conservative; total run time is a few minutes.
MIN_INTERVAL = {
    "www.gutenberg.org": 1.0,
    "gutendex.com": 0.5,
    "archive.org": 1.5,
    "en.wikisource.org": 1.0,
    "zh.wikisource.org": 0.55,
    "sa.wikisource.org": 0.7,
    "gretil.sub.uni-goettingen.de": 1.0,
    "pubchem.ncbi.nlm.nih.gov": 0.25,
    "www.ebi.ac.uk": 0.5,
    "rest.kegg.jp": 0.5,
    "eutils.ncbi.nlm.nih.gov": 0.4,
    "api.gbif.org": 0.3,
    "powo.science.kew.org": 0.5,
    "query.wikidata.org": 1.0,
    "api.iseg-ethno.example": 1.0,
}
_DEFAULT_INTERVAL = 0.5

_last_call: dict[str, float] = {}


class FetchError(RuntimeError):
    pass


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    return s


_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = session()
    return _SESSION


def _throttle(url: str) -> None:
    from urllib.parse import urlparse

    host = urlparse(url).netloc
    interval = MIN_INTERVAL.get(host, _DEFAULT_INTERVAL)
    last = _last_call.get(host, 0.0)
    wait = interval - (time.monotonic() - last)
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def _cache_path(url: str, kind: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    ext = "json" if kind == "json" else "txt"
    return CACHE / f"{h}.{ext}"


def get_json(url: str, params: dict | None = None, *, timeout: int = 40,
             retries: int = 4, cache: bool = True, cache_ttl: int = 7 * 86400) -> Any:
    """GET a JSON document with retry, throttle and on-disk cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = url + ("?" + json.dumps(params, sort_keys=True) if params else "")
    cpath = _cache_path(key, "json")
    if cache and cpath.exists():
        age = time.time() - cpath.stat().st_mtime
        if age < cache_ttl:
            try:
                return json.loads(cpath.read_text(encoding="utf-8"))
            except Exception:
                pass
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            _throttle(url)
            r = _get_session().get(url, params=params, timeout=timeout)
            if r.status_code in (200, 201):
                data = r.json()
                if cache:
                    cpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                return data
            if r.status_code == 404:
                raise FetchError(f"404 {r.url}")
            if r.status_code in (429, 500, 502, 503, 504):
                last_err = FetchError(f"HTTP {r.status_code} {r.url}")
            else:
                raise FetchError(f"HTTP {r.status_code} {r.url}")
        except FetchError:
            raise
        except Exception as e:  # network/timeout/JSON
            last_err = e
        time.sleep((2 ** attempt) * 0.8 + random.random() * 0.4)
    raise FetchError(f"failed {url}: {last_err}")


def get_text(url: str, params: dict | None = None, *, timeout: int = 120,
             retries: int = 4) -> str:
    """GET a text document (utf-8 / latin-1 fallback) with retry and throttle."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            _throttle(url)
            r = _get_session().get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                if not r.encoding or r.encoding.lower() in ("iso-8859-1", "latin-1"):
                    # requests falls back to latin-1 when the server omits a charset;
                    # try utf-8 first because most of these archives are utf-8.
                    try:
                        return r.content.decode("utf-8")
                    except UnicodeDecodeError:
                        return r.content.decode("windows-1252", errors="replace")
                return r.text
            if r.status_code == 404:
                raise FetchError(f"404 {r.url}")
            last_err = FetchError(f"HTTP {r.status_code} {r.url}")
        except FetchError:
            raise
        except Exception as e:
            last_err = e
        time.sleep((2 ** attempt) * 1.0 + random.random() * 0.5)
    raise FetchError(f"failed {url}: {last_err}")


def download(url: str, dest: Path, *, timeout: int = 300, retries: int = 4,
             min_bytes: int = 1024) -> Path:
    """Download ``url`` to ``dest`` atomically. Skips when already present.

    Returns the destination path. Raises FetchError on failure.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            _throttle(url)
            with _get_session().get(url, stream=True, timeout=timeout) as r:
                if r.status_code != 200:
                    if r.status_code in (429, 500, 502, 503, 504):
                        last_err = FetchError(f"HTTP {r.status_code} {url}")
                        time.sleep((2 ** attempt) * 1.5)
                        continue
                    raise FetchError(f"HTTP {r.status_code} {url}")
                n = 0
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if chunk:
                            fh.write(chunk)
                            n += len(chunk)
                if n < min_bytes:
                    tmp.unlink(missing_ok=True)
                    last_err = FetchError(f"suspiciously small ({n} bytes) {url}")
                    continue
                os.replace(tmp, dest)
                return dest
        except FetchError:
            raise
        except Exception as e:
            last_err = e
            time.sleep((2 ** attempt) * 1.5 + random.random())
    tmp.unlink(missing_ok=True)
    raise FetchError(f"failed download {url}: {last_err}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
