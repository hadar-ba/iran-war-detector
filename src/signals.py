"""
Signal detection: runs specific GDELT queries to detect active signals in the 7-day window.
Results feed into docs/data/latest.json for the public dashboard.
"""

import os
import sys
import requests
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdelt_client import GDELT_BASE, CACHE_DIR, _cache_key, _cache_load, _cache_save, RATE_SLEEP

SIGNAL_DEFS = {
    "diplomatic_breakdown": {
        "query": "Iran AND Israel AND (diplomacy OR ceasefire OR deadline OR ultimatum OR negotiations)",
        "name_en": "Diplomatic breakdown signals",
        "name_he": "סיגנלי קריסה דיפלומטית",
        "desc_en": "Reports of stalled negotiations, ultimatums, or diplomatic breakdowns",
        "desc_he": "דיווחים על קריסת משא ומתן, אולטימטומים, או פריצת יחסים דיפלומטיים",
        "baseline_weekly": 4,
    },
    "supreme_leader": {
        "query": "Iran AND Khamenei AND Israel",
        "name_en": "Iranian leadership statements",
        "name_he": "הצהרות ההנהגה האיראנית",
        "desc_en": "Statements by Iran's Supreme Leader referencing Israel",
        "desc_he": "הצהרות המנהיג העליון של איראן המתייחסות לישראל",
        "baseline_weekly": 3,
    },
    "trump_china": {
        "query": "Iran AND Israel AND Trump AND China",
        "name_en": "US-China diplomatic activity",
        "name_he": 'פעילות דיפלומטית של ארה"ב-סין',
        "desc_en": "Trump/US-China diplomatic moves related to the Iran-Israel dynamic",
        "desc_he": "מהלכים דיפלומטיים של טראמפ/ארה\"ב-סין בהקשר ישראל-איראן",
        "baseline_weekly": 2,
    },
    "military_strike": {
        "query": "Iran AND Israel AND (airstrike OR missile OR military strike OR escalation OR retaliation)",
        "name_en": "Military action indicators",
        "name_he": "מדדי פעילות צבאית",
        "desc_en": "Reports of strikes, missile activity, or military escalation",
        "desc_he": "דיווחים על תקיפות, פעילות טילים, או הסלמה צבאית",
        "baseline_weekly": 6,
    },
}

_ORDER = {"high": 0, "elevated": 1, "baseline": 2, "unknown": 3}


def _intensity(count, baseline):
    if count is None or baseline == 0:
        return "unknown"
    if count >= baseline * 3:
        return "high"
    if count >= baseline * 1.5:
        return "elevated"
    return "baseline"


def detect_signals(start7: str, end7: str) -> list[dict]:
    """
    Run all signal queries for the 7-day window.
    Returns list of signal dicts matching docs/data/latest.json schema.
    Fails fast on 429 — returns count=None with error logged.
    """
    results = []
    for sig_id, sig in SIGNAL_DEFS.items():
        params = {
            "query": sig["query"],
            "mode": "artlist",
            "format": "json",
            "startdatetime": start7,
            "enddatetime": end7,
            "sourcelang": "english",
            "maxrecords": "50",
        }
        cached = _cache_load(params, ttl_seconds=6 * 3600)
        if cached is not None:
            arts, err = cached, None
        else:
            arts, err = [], None
            try:
                r = requests.get(GDELT_BASE, params=params, timeout=20)
                if r.status_code == 429:
                    err = "429 rate-limited"
                elif r.ok:
                    text = r.text.strip()
                    if text and text.startswith("{"):
                        arts = r.json().get("articles", [])
                        _cache_save(params, arts)
                    else:
                        err = "non-JSON response"
                else:
                    err = f"HTTP {r.status_code}"
            except Exception as e:
                err = str(e)
            time.sleep(RATE_SLEEP)

        count = len(arts) if err is None else None
        intensity = _intensity(count, sig["baseline_weekly"])

        results.append({
            "id": sig_id,
            "intensity": intensity,
            "name_en": sig["name_en"],
            "name_he": sig["name_he"],
            "description_en": sig["desc_en"],
            "description_he": sig["desc_he"],
            "count_current": count,
            "count_baseline_avg": sig["baseline_weekly"],
            "error": err,
            "example_urls": [a.get("url", "") for a in arts[:3]],
        })

    results.sort(key=lambda s: _ORDER.get(s["intensity"], 3))
    return results
