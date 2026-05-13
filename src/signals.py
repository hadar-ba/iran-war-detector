"""
Signal detection: runs specific GDELT queries to detect active signals in the 7-day window.
Uses timelinecount over 35 days for real article counts and WoW/MoM ratios.
Uses artlist (max 250) for article display.
Results feed into docs/data/latest.json for the public dashboard.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdelt_client import get_signal_timeline_count, get_signal_artlist_custom

SIGNAL_DEFS = {
    "diplomatic_breakdown": {
        "query": "Iran AND Israel AND (diplomacy OR ceasefire OR deadline OR ultimatum OR negotiations)",
        "name_en": "Diplomatic breakdown signals",
        "name_he": "קריסת משא ומתן דיפלומטי",
        "desc_en": "Reports of stalled negotiations, ultimatums, or diplomatic breakdowns",
        "desc_he": "דיווחים על קריסת משא ומתן, אולטימטומים, או פריצת יחסים דיפלומטיים",
    },
    "supreme_leader": {
        "query": "Iran AND Khamenei AND Israel",
        "name_en": "Iranian leadership statements",
        "name_he": "הצהרות ההנהגה האיראנית",
        "desc_en": "Statements by Iran's Supreme Leader referencing Israel",
        "desc_he": "הצהרות המנהיג העליון של איראן המתייחסות לישראל",
    },
    "trump_china": {
        "query": "Iran AND Israel AND Trump AND China",
        "name_en": "US-China diplomatic activity",
        "name_he": 'פעילות דיפלומטית ארה"ב-סין',
        "desc_en": "Trump/US-China diplomatic moves related to the Iran-Israel dynamic",
        "desc_he": 'מהלכים דיפלומטיים של טראמפ/ארה"ב-סין בהקשר ישראל-איראן',
    },
    "military_strike": {
        "query": "Iran AND Israel AND (airstrike OR missile OR military strike OR escalation OR retaliation)",
        "name_en": "Military action indicators",
        "name_he": "מדדי פעילות צבאית",
        "desc_en": "Reports of strikes, missile activity, or military escalation",
        "desc_he": "דיווחים על תקיפות, פעילות טילים, או הסלמה צבאית",
    },
}

_ORDER = {"high": 0, "elevated": 1, "baseline": 2, "unknown": 3}


def _split_timeline(entries: list, end_str: str) -> dict:
    """
    Bucket timelinecount entries into weekly sums relative to end_str.
    Returns: week0 (last 7d), week1 (8-14d ago), week4 (29-35d ago), total35
    """
    end_dt = datetime.strptime(end_str, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    buckets = {"week0": 0, "week1": 0, "week4": 0, "total35": 0}
    for e in entries:
        raw = e.get("date", "")
        try:
            clean = raw.replace("T", "").replace("Z", "")[:8]
            entry_dt = datetime.strptime(clean, "%Y%m%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        age = (end_dt - entry_dt).days
        val = int(e.get("value", 0))
        if 0 <= age < 7:
            buckets["week0"] += val
        elif 7 <= age < 14:
            buckets["week1"] += val
        elif 28 <= age < 35:
            buckets["week4"] += val
        if 0 <= age < 35:
            buckets["total35"] += val
    return buckets


def _safe_ratio(a, b):
    if not a or not b:
        return None
    return round(a / b, 1)


def _intensity(count, baseline):
    if count is None or baseline is None or baseline == 0:
        return "unknown"
    if count >= baseline * 3:
        return "high"
    if count >= baseline * 1.5:
        return "elevated"
    return "baseline"


def detect_signals(start7: str, end7: str) -> list[dict]:
    """
    Run all signal queries for the 7-day window.
    - Fetches 35-day timelinecount for real counts and WoW/MoM ratios.
    - Fetches 7-day artlist (max 250) for article display.
    """
    end_dt = datetime.strptime(end7, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    start35 = (end_dt - timedelta(days=35)).strftime("%Y%m%d%H%M%S")

    results = []
    for sig_id, sig in SIGNAL_DEFS.items():
        # --- 35-day timelinecount for real counts and ratios ---
        tl_entries, tl_err = get_signal_timeline_count(sig["query"], start35, end7)
        if tl_err or not tl_entries:
            week0 = week1 = monthly_avg = None
            ratio_wow = ratio_mom = None
        else:
            buckets = _split_timeline(tl_entries, end7)
            week0 = buckets["week0"]
            week1 = buckets["week1"]
            weekly_avg_35d = buckets["total35"] // 5 if buckets["total35"] > 0 else 0
            monthly_avg = weekly_avg_35d if weekly_avg_35d > 0 else None
            ratio_wow = _safe_ratio(week0, week1)
            ratio_mom = _safe_ratio(week0, monthly_avg)

        # --- 7-day artlist for article display (max 250, GDELT hard cap) ---
        arts, art_err = get_signal_artlist_custom(sig["query"], start7, end7, max_records=250)
        err = tl_err or art_err

        baseline = monthly_avg
        intensity = _intensity(week0, baseline)

        results.append({
            "id": sig_id,
            "intensity": intensity,
            "name_en": sig["name_en"],
            "name_he": sig["name_he"],
            "description_en": sig["desc_en"],
            "description_he": sig["desc_he"],
            "count_current": week0,
            "count_prev_week": week1,
            "count_baseline_avg": baseline,
            "ratio_wow": ratio_wow,
            "ratio_mom": ratio_mom,
            "error": err,
            "example_urls": [a.get("url", "") for a in arts[:3]],
            "articles": [
                {"url": a.get("url", ""), "title": a.get("title", ""),
                 "domain": a.get("domain", ""), "seendate": a.get("seendate", "")}
                for a in arts
            ],
        })

    results.sort(key=lambda s: _ORDER.get(s["intensity"], 3))
    return results
