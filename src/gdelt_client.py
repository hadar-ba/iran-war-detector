"""
GDELT DOC API v2 client with disk caching and rate limiting.

Key API facts (verified empirically in Stage 1):
- timelinevol sourcelang does NOT filter results — returns global metric regardless of language.
  Use artlist for language-specific article counts and domain sampling.
- artlist capped at 250 records per query.
- Rate limit: sleep 7s between requests; exponential backoff on 429.
- Query must not use parentheses (gets URL-encoded, GDELT rejects).
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from collections import Counter

import requests

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
BASE_QUERY = "Iran AND Israel"
LANGUAGES = ["english", "hebrew", "persian"]

RATE_SLEEP = 15         # seconds between requests (conservative to avoid 429)
CACHE_TTL_CURRENT = 6 * 3600   # 6 hours for current-period queries
CACHE_TTL_REFERENCE = None      # never expire for reference period queries

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(_REPO_ROOT, "data", "cache")


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(params: dict) -> str:
    canonical = json.dumps(params, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def _cache_load(params: dict, ttl_seconds) -> dict | None:
    path = _cache_path(_cache_key(params))
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        entry = json.load(f)
    if ttl_seconds is None:
        return entry["data"]
    age = time.time() - entry["ts"]
    if age < ttl_seconds:
        return entry["data"]
    return None


def _cache_save(params: dict, data: dict) -> None:
    path = _cache_path(_cache_key(params))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "data": data}, f)


# ---------------------------------------------------------------------------
# Raw HTTP request with retry
# ---------------------------------------------------------------------------

def _gdelt_request(params: dict, retries: int = 2) -> tuple[dict | None, str | None]:
    """GET with fail-fast on 429 (no backoff sleep). Returns (data, error)."""
    for attempt in range(retries):
        try:
            r = requests.get(GDELT_BASE, params=params, timeout=30)
            if r.status_code == 429:
                print(f"    [429] rate-limited — skipping (attempt {attempt+1}/{retries})", flush=True)
                return None, "429 rate-limited"
            r.raise_for_status()
            text = r.text.strip()
            if not text or not text.startswith("{"):
                return None, f"non-JSON body: {repr(text[:120])}"
            return r.json(), None
        except requests.exceptions.ConnectionError as e:
            print(f"    [ERR] connection error: {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
        except requests.exceptions.RequestException as e:
            print(f"    [ERR] request error: {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(10)
    return None, "all retries failed"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_volume_timeline(start: str, end: str, is_reference: bool = False) -> tuple[list, str | None]:
    """
    Fetch timelinevol for the date range. Returns (entries, error).
    entries: [{"date": "20240323T000000Z", "value": 0.25}, ...]

    NOTE: sourcelang is intentionally omitted — it does not filter timelinevol.
    One call covers all languages (global metric).
    """
    params = {
        "query": BASE_QUERY,
        "mode": "timelinevol",
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
    }
    ttl = CACHE_TTL_REFERENCE if is_reference else CACHE_TTL_CURRENT
    cached = _cache_load(params, ttl)
    if cached is not None:
        return cached, None

    data, err = _gdelt_request(params)
    time.sleep(RATE_SLEEP)
    if data is None:
        return [], err
    try:
        tl = data.get("timeline", [])
        entries = tl[0]["data"] if tl and tl[0].get("data") else []
        _cache_save(params, entries)
        return entries, None
    except Exception as e:
        return [], f"parse error: {e}"


def get_volume_timeline_tone(start: str, end: str, is_reference: bool = False) -> tuple[list, str | None]:
    """
    Fetch timelinetone for the date range. Returns (entries, error).
    entries: [{"date": ..., "value": <average tone>}, ...]
    """
    params = {
        "query": BASE_QUERY,
        "mode": "timelinetone",
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
    }
    ttl = CACHE_TTL_REFERENCE if is_reference else CACHE_TTL_CURRENT
    cached = _cache_load(params, ttl)
    if cached is not None:
        return cached, None

    data, err = _gdelt_request(params)
    time.sleep(RATE_SLEEP)
    if data is None:
        return [], err
    try:
        tl = data.get("timeline", [])
        entries = tl[0]["data"] if tl and tl[0].get("data") else []
        _cache_save(params, entries)
        return entries, None
    except Exception as e:
        return [], f"parse error: {e}"


def get_artlist(start: str, end: str, lang: str, max_records: int = 250,
                is_reference: bool = False) -> tuple[list, str | None]:
    """
    Fetch up to max_records articles for the given language.
    Returns (articles, error).
    articles: [{"url": ..., "domain": ..., "title": ..., "socialimage": ..., "seendate": ...}, ...]

    This is the correct way to get language-specific data — timelinevol ignores sourcelang.
    """
    params = {
        "query": BASE_QUERY,
        "mode": "artlist",
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
        "sourcelang": lang,
        "maxrecords": str(max_records),
    }
    ttl = CACHE_TTL_REFERENCE if is_reference else CACHE_TTL_CURRENT
    cached = _cache_load(params, ttl)
    if cached is not None:
        return cached, None

    data, err = _gdelt_request(params)
    time.sleep(RATE_SLEEP)
    if data is None:
        return [], err
    try:
        articles = data.get("articles", [])
        _cache_save(params, articles)
        return articles, None
    except Exception as e:
        return [], f"parse error: {e}"


def get_domain_counts(start: str, end: str, lang: str,
                      is_reference: bool = False) -> tuple[Counter, str | None]:
    """
    Return a Counter of domain -> article_count for the language sample (250 articles).
    Domain is extracted from the article's "domain" field or parsed from its URL.
    """
    articles, err = get_artlist(start, end, lang, max_records=250, is_reference=is_reference)
    if err:
        return Counter(), err
    counts = Counter()
    for art in articles:
        domain = art.get("domain", "")
        if not domain:
            domain = urlparse(art.get("url", "")).netloc.lower().lstrip("www.")
        if domain:
            counts[domain] += 1
    return counts, None


def get_article_count(start: str, end: str, lang: str,
                      is_reference: bool = False) -> tuple[int, str | None]:
    """
    Return the number of articles returned by artlist for the language (capped at 250).
    Used as a proxy for language-specific volume when timelinevol is not language-filtered.
    """
    articles, err = get_artlist(start, end, lang, max_records=250, is_reference=is_reference)
    return len(articles), err


def get_current_window(days: int = 21) -> tuple[str, str]:
    """
    Return (startdatetime, enddatetime) for an analysis window of `days` length
    ending at the current UTC time (YYYYMMDDHHMMSS format).
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    fmt = "%Y%m%d%H%M%S"
    return start.strftime(fmt), now.strftime(fmt)
