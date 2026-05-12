#!/usr/bin/env python3
"""
Stage 1: Verify GDELT DOC API coverage for all reference periods.
Generates reports/sanity_check.md.

Verified API behaviour:
- Rate limit: 1 request per 5 seconds; use 7s to be safe
- timelinevol JSON: {"timeline": [{"series": "Volume Intensity", "data": [{"date": ..., "value": ...}]}]}
- "value" is normalized Volume Intensity (not raw article count)
- "domain" mode is invalid; use artlist to sample domains
- artlist JSON: {"articles": [{"url": ..., "domain": ..., "title": ..., ...}]}
- 429 response body is plain text (not JSON)

Run from repo root: python src/stage1_sanity_check.py
"""

import requests
import time
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse
from collections import Counter

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(REPO_ROOT, "reports", "sanity_check.md")

REFERENCE_PERIODS = {
    "PRE_APR24":   ("20240323000000", "20240412235959", "Mar 23 – Apr 12, 2024", "pre-round"),
    "PRE_OCT24":   ("20240910000000", "20240930235959", "Sep 10 – Sep 30, 2024", "pre-round"),
    "PRE_JUN25":   ("20250523000000", "20250612235959", "May 23 – Jun 12, 2025", "pre-round"),
    "PRE_FEB26":   ("20260207000000", "20260227235959", "Feb 7 – Feb 27, 2026",  "pre-round"),
    "POST_APR24":  ("20240501000000", "20240521235959", "May 1 – May 21, 2024",  "post-ceasefire"),
    "POST_OCT24":  ("20241101000000", "20241121235959", "Nov 1 – Nov 21, 2024",  "post-ceasefire"),
    "POST_JUN25":  ("20250701000000", "20250721235959", "Jul 1 – Jul 21, 2025",  "post-ceasefire"),
    "POST_FEB26":  ("20260415000000", "20260505235959", "Apr 15 – May 5, 2026",  "post-ceasefire"),
    "QUIET_FEB25": ("20250214000000", "20250228235959", "Feb 14 – Feb 28, 2025", "quiet"),
    "QUIET_SEP25": ("20250901000000", "20250921235959", "Sep 1 – Sep 21, 2025",  "quiet"),
    "QUIET_JAN26": ("20260101000000", "20260121235959", "Jan 1 – Jan 21, 2026",  "quiet"),
}

LANGUAGES = ["english", "hebrew", "persian"]
BASE_QUERY = "Iran AND Israel"
RATE_SLEEP = 7       # seconds between each request (API limit is 5s)
MIN_DAYS = 5         # warn if fewer active days than this


def gdelt_request(params, retries=4):
    """GET request with 429-aware retry. Returns (dict, None) or (None, error_str)."""
    for attempt in range(retries):
        try:
            r = requests.get(GDELT_BASE, params=params, timeout=30)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"\n    [429] rate-limited — waiting {wait}s (attempt {attempt+1}/{retries})", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            text = r.text.strip()
            if not text or not text.startswith("{"):
                return None, f"non-JSON body: {repr(text[:100])}"
            return r.json(), None
        except requests.exceptions.ConnectionError as e:
            msg = f"connection error: {e}"
            print(f"\n    [ERR] {msg}", flush=True)
            if attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
        except requests.exceptions.RequestException as e:
            msg = f"request error: {e}"
            print(f"\n    [ERR] {msg}", flush=True)
            if attempt < retries - 1:
                time.sleep(10)
    return None, "all retries failed"


def get_volume(start, end, lang):
    """Return (total_intensity: float, days_with_data: int, error: str|None)."""
    params = {"query": BASE_QUERY, "mode": "timelinevol", "format": "json",
              "startdatetime": start, "enddatetime": end, "sourcelang": lang}
    data, err = gdelt_request(params)
    time.sleep(RATE_SLEEP)
    if data is None:
        return None, None, err
    try:
        tl = data.get("timeline", [])
        if not tl or not tl[0].get("data"):
            return 0.0, 0, None
        entries = tl[0]["data"]
        total = round(sum(e.get("value", 0) for e in entries), 4)
        days = sum(1 for e in entries if e.get("value", 0) > 0)
        return total, days, None
    except Exception as e:
        return None, None, f"parse error: {e}"


def get_sample_domains(start, end, lang, top_n=10):
    """Return ([(domain, count), ...], error|None) from a 250-article sample."""
    params = {"query": BASE_QUERY, "mode": "artlist", "format": "json",
              "startdatetime": start, "enddatetime": end, "sourcelang": lang,
              "maxrecords": "250"}
    data, err = gdelt_request(params)
    time.sleep(RATE_SLEEP)
    if data is None:
        return [], err
    try:
        articles = data.get("articles", [])
        counts = Counter()
        for art in articles:
            # artlist articles may have a direct "domain" field
            domain = art.get("domain", "")
            if not domain:
                domain = urlparse(art.get("url", "")).netloc.lower().lstrip("www.")
            if domain:
                counts[domain] += 1
        return counts.most_common(top_n), None
    except Exception as e:
        return [], f"parse error: {e}"


EXPECTED_SOURCES = {
    "english": {"reuters.com", "apnews.com", "bbc.com", "timesofisrael.com",
                "jpost.com", "aljazeera.com", "bloomberg.com",
                "washingtonpost.com", "nytimes.com", "axios.com"},
    "hebrew": {"ynet.co.il", "walla.co.il", "haaretz.co.il", "maariv.co.il",
               "globes.co.il", "n12.co.il", "israelhayom.co.il"},
    "persian": {"tasnimnews.com", "farsnews.ir", "irna.ir", "isna.ir",
                "mehrnews.com", "iranintl.com", "radiofarda.com", "voanews.com"},
}


def main():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_calls = len(REFERENCE_PERIODS) * len(LANGUAGES) * 2
    eta_min = total_calls * RATE_SLEEP // 60
    print(f"Stage 1 sanity check — {generated_at}")
    print(f"Query: '{BASE_QUERY}' | {total_calls} API calls | ~{eta_min} min\n")

    results = {}
    warnings = []

    for period_id, (start, end, label, ptype) in REFERENCE_PERIODS.items():
        print(f"[{period_id}]  {label}  ({ptype})")
        results[period_id] = {"label": label, "type": ptype,
                               "start": start, "end": end, "langs": {}}

        for lang in LANGUAGES:
            print(f"  {lang:8s} vol... ", end="", flush=True)
            intensity, days, vol_err = get_volume(start, end, lang)
            print(f"domains... ", end="", flush=True)
            domains, dom_err = get_sample_domains(start, end, lang)

            results[period_id]["langs"][lang] = {
                "intensity_total": intensity,
                "days_with_data": days,
                "vol_error": vol_err,
                "top_domains": domains,
                "dom_error": dom_err,
            }

            if intensity is None:
                status = f"vol=ERR ({vol_err})"
                warnings.append(f"{period_id}/{lang}: volume failed - {vol_err}")
            elif days is not None and days < MIN_DAYS:
                status = f"vol={intensity:.2f} days={days} [LOW]"
                warnings.append(f"{period_id}/{lang}: only {days} active days (min={MIN_DAYS})")
            else:
                status = f"vol={intensity:.2f} days={days} [OK]"

            if dom_err:
                status += " | domains=ERR"
                warnings.append(f"{period_id}/{lang}: domains failed - {dom_err}")
            elif not domains:
                status += " | domains=empty"
            else:
                status += f" | {len(domains)} domains"

            print(status, flush=True)

    write_report(results, warnings, generated_at)
    print(f"\nReport: {REPORT_PATH}")

    if warnings:
        print(f"\n[!] {len(warnings)} warnings:")
        for w in warnings:
            print(f"   - {w}")
        sys.exit(1)
    else:
        print("\n[OK] All coverage checks passed.")
        sys.exit(0)


def write_report(results, warnings, generated_at):
    lines = [
        "# Stage 1: GDELT Coverage Sanity Check",
        f"\n**Generated:** {generated_at}",
        f"**Query:** `{BASE_QUERY}`",
        "**Metric:** Volume Intensity (normalized 0–1 scale; not raw article count)",
        f"**Threshold:** ≥{MIN_DAYS} days with non-zero coverage per language/period\n",
    ]

    if warnings:
        lines += ["## ⚠️ Warnings\n"] + [f"- {w}" for w in warnings] + [""]
    else:
        lines.append("## ✅ All periods passed coverage checks\n")

    lines += [
        "## Coverage Summary\n",
        "| Period | Type | Window | English | Hebrew | Persian |",
        "|--------|------|--------|---------|--------|---------|",
    ]

    for pid, info in results.items():
        def fmt(ld):
            d = ld.get("days_with_data")
            if ld.get("intensity_total") is None:
                return "❌ ERR"
            if d is not None and d < MIN_DAYS:
                return f"⚠️ {d}d"
            return f"✅ {d}d"
        en = fmt(info["langs"].get("english", {}))
        he = fmt(info["langs"].get("hebrew", {}))
        fa = fmt(info["langs"].get("persian", {}))
        lines.append(f"| {pid} | {info['type']} | {info['label']} | {en} | {he} | {fa} |")

    lines.append("\n## Detailed Results\n")

    for pid, info in results.items():
        lines.append(f"### {pid} — {info['label']} ({info['type']})\n")
        for lang in LANGUAGES:
            ld = info["langs"].get(lang, {})
            intensity = ld.get("intensity_total")
            days = ld.get("days_with_data")
            domains = ld.get("top_domains", [])

            if intensity is None:
                flag = "❌ FAILED"
            elif days is not None and days < MIN_DAYS:
                flag = f"⚠️ LOW"
            else:
                flag = "✅"

            lines.append(f"**{lang.capitalize()}** {flag}")
            if ld.get("vol_error"):
                lines.append(f"- Error: {ld['vol_error']}")
            else:
                lines.append(f"- Volume Intensity total: {intensity}")
                lines.append(f"- Days with non-zero coverage: {days}")

            if domains:
                expected = EXPECTED_SOURCES.get(lang, set())
                found = {d for d, _ in domains} & expected
                lines.append(f"- Expected sources found in sample: {sorted(found) if found else 'none'}")
                lines.append("- Top domains (sample of 250 articles):")
                for domain, count in domains:
                    star = " ⭐" if domain in expected else ""
                    lines.append(f"  - `{domain}` ({count}){star}")
            elif ld.get("dom_error"):
                lines.append(f"- Domain sample error: {ld['dom_error']}")
            else:
                lines.append("- No domain data")
            lines.append("")

    lines += [
        "---",
        "*Stage 1 of the Iran-Israel Conflict Pattern Detector pipeline.*",
    ]

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
