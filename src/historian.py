"""
Historian: saves run results, renders reports/latest.md, and writes
docs/data/latest.json + docs/data/history.json for the public dashboard.
"""

import json
import os
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR   = os.path.join(_REPO_ROOT, "data", "results")
LATEST_REPORT = os.path.join(_REPO_ROOT, "reports", "latest.md")
UI_DATA_DIR   = os.path.join(_REPO_ROOT, "docs", "data")
UI_LATEST     = os.path.join(UI_DATA_DIR, "latest.json")
UI_HISTORY    = os.path.join(UI_DATA_DIR, "history.json")

WARN_THRESHOLD   = 0.70
YELLOW_THRESHOLD = 0.50
HISTORY_MAX      = 60   # keep last 60 runs (~30 days at 2×/day)

PERIOD_LABELS = {
    "PRE_APR24":  {"en": "the period before Iran's first direct attack on Israel (April 2024)",
                   "he": "התקופה שלפני המתקפה הישירה הראשונה של איראן על ישראל (אפריל 2024)"},
    "PRE_OCT24":  {"en": "the period before Iran's October 2024 missile barrage",
                   "he": "התקופה שלפני מטח הטילים האיראני (אוקטובר 2024)"},
    "PRE_JUN25":  {"en": "the period before the June 2025 exchange",
                   "he": "התקופה שלפני הסיבוב ביוני 2025"},
    "PRE_FEB26":  {"en": "the period before Operation Lion's Roar (February 2026)",
                   "he": "התקופה שלפני מבצע 'שאגת הארי' (פברואר 2026)"},
    "POST_APR24": {"en": "the post-ceasefire period (May 2024)",
                   "he": "תקופת שביתת הנשק (מאי 2024)"},
    "POST_OCT24": {"en": "the post-ceasefire period (November 2024)",
                   "he": "תקופת שביתת הנשק (נובמבר 2024)"},
    "POST_JUN25": {"en": "the aftermath of the June 2025 exchange",
                   "he": "תקופת לאחר הסיבוב ביוני 2025"},
    "POST_FEB26": {"en": "the post-Lion's Roar period (April–May 2026)",
                   "he": "התקופה שלאחר 'שאגת הארי' (אפריל–מאי 2026)"},
    "QUIET_FEB25":{"en": "a quiet period (February 2025)",
                   "he": "תקופה שקטה (פברואר 2025)"},
    "QUIET_SEP25":{"en": "a quiet period (September 2025)",
                   "he": "תקופה שקטה (ספטמבר 2025)"},
    "QUIET_JAN26":{"en": "a relatively quiet period (January 2026)",
                   "he": "תקופה יחסית שקטה (ינואר 2026)"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status(max_pre_7: float) -> str:
    if max_pre_7 >= WARN_THRESHOLD:   return "red"
    if max_pre_7 >= YELLOW_THRESHOLD: return "yellow"
    return "green"


def _period_label(pid: str, lang: str) -> str:
    return PERIOD_LABELS.get(pid, {}).get(lang, pid)


def _best_pre(similarities: list[dict]) -> tuple[str | None, float]:
    pre = [s for s in similarities if s.get("is_pre_round")]
    if not pre:
        return None, 0.0
    best = max(pre, key=lambda s: s["composite_score"])
    return best["reference_id"], best["composite_score"]


def _best_match(similarities: list[dict]) -> tuple[str | None, float]:
    if not similarities:
        return None, 0.0
    best = max(similarities, key=lambda s: s["composite_score"])
    return best["reference_id"], best["composite_score"]


# ---------------------------------------------------------------------------
# Narrative generation (template-based, no LLM)
# ---------------------------------------------------------------------------

def generate_narratives(
    status: str,
    max_pre_7: float, max_pre_21: float,
    closest_pre_7: str | None,
    closest_21: str | None,
    spike: float,
    signals: list[dict],
) -> dict:
    pct7  = round(max_pre_7  * 100)
    pct21 = round(max_pre_21 * 100)
    label7_en = _period_label(closest_pre_7, "en") if closest_pre_7 else "any reference period"
    label7_he = _period_label(closest_pre_7, "he") if closest_pre_7 else "אף תקופת ייחוס"
    label21_en = _period_label(closest_21,   "en") if closest_21 else "a reference period"
    label21_he = _period_label(closest_21,   "he") if closest_21 else "תקופת ייחוס"

    high_sigs   = [s for s in signals if s["intensity"] == "high"]
    elev_sigs   = [s for s in signals if s["intensity"] == "elevated"]
    known_sigs  = [s for s in signals if s["intensity"] in ("high", "elevated", "baseline")]
    spike_note_en = (f" The 7-day reading is {round(spike*100)} points above the 21-day baseline,"
                     " suggesting a recent and rapid development."
                     if spike > 0.10 else "")
    spike_note_he = (f" הקריאה ל-7 ימים גבוהה ב-{round(spike*100)} נקודות מהבסיס ל-21 יום,"
                     " מה שמצביע על התפתחות מהירה ועדכנית."
                     if spike > 0.10 else "")

    if status == "green":
        sum_en = "News patterns are within the normal range — no elevated signals detected."
        sum_he = "דפוסי החדשות נמצאים בטווח הנורמלי — לא זוהו סיגנלים מוגברים."
        ctx_en = (f"In the last 7 days, news volume and tone resemble {label7_en or 'a quiet period'} "
                  f"({pct7}% similarity). The 21-day picture is consistent: {pct21}% similarity to "
                  f"{label21_en}. All monitored signals are at or near baseline.")
        ctx_he = (f"ב-7 הימים האחרונים, נפח החדשות והטון דומים ל{label7_he or 'תקופה שקטה'} "
                  f"({pct7}% דמיון). התמונה ל-21 יום עקבית: {pct21}% דמיון ל{label21_he}. "
                  f"כל הסיגנלים המנוטרים נמצאים ברמת הבסיס.")

    elif status == "yellow":
        sig_note_en = (f" {len(high_sigs + elev_sigs)} monitored signal(s) are elevated." if (high_sigs or elev_sigs) else "")
        sig_note_he = (f" {len(high_sigs + elev_sigs)} סיגנל/ים מנוטרים מוגברים." if (high_sigs or elev_sigs) else "")
        sum_en = f"Short-term patterns show borderline similarity to pre-conflict periods ({pct7}%)."
        sum_he = f"דפוסי הטווח הקצר מראים דמיון גבולי לתקופות טרום עימות ({pct7}%)."
        ctx_en = (f"In the last 7 days, news patterns are starting to resemble {label7_en} "
                  f"({pct7}% similarity).{sig_note_en}{spike_note_en} "
                  f"The 21-day picture is {'similar' if pct21 >= 50 else 'calmer'} at {pct21}% similarity to {label21_en}.")
        ctx_he = (f"ב-7 הימים האחרונים, דפוסי החדשות מתחילים להידמות ל{label7_he} "
                  f"({pct7}% דמיון).{sig_note_he}{spike_note_he} "
                  f"התמונה ל-21 יום {'דומה' if pct21 >= 50 else 'רגועה יותר'} עם {pct21}% דמיון ל{label21_he}.")

    else:  # red
        sig_note_en = (f" {len(high_sigs)} signal(s) are at high intensity, {len(elev_sigs)} elevated." if known_sigs else "")
        sig_note_he = (f" {len(high_sigs)} סיגנל/ים עם עוצמה גבוהה, {len(elev_sigs)} מוגברים." if known_sigs else "")
        sum_en = (f"Short-term news patterns closely resemble {label7_en} "
                  f"({pct7}% similarity). This exceeds the warning threshold.")
        sum_he = (f"דפוסי החדשות לטווח קצר דומים מאוד ל{label7_he} "
                  f"({pct7}% דמיון). זה חורג מסף האזהרה.")
        ctx_en = (f"In the last 7 days, news coverage patterns closely match those observed before "
                  f"{label7_en}.{sig_note_en}{spike_note_en} "
                  f"The 21-day picture shows {pct21}% similarity to {label21_en} — "
                  f"{'the elevated level has been building' if pct21 >= 50 else 'the recent spike is new and sharp'}.")
        ctx_he = (f"ב-7 הימים האחרונים, דפוסי הכיסוי התקשורתי דומים מאוד לאלו שנצפו לפני "
                  f"{label7_he}.{sig_note_he}{spike_note_he} "
                  f"התמונה ל-21 יום מראה {pct21}% דמיון ל{label21_he} — "
                  f"{'ההסלמה בנויה לאורך זמן' if pct21 >= 50 else 'הספייק האחרון חדש וחד'}.")

    return {"summary_en": sum_en, "summary_he": sum_he,
            "context_en": ctx_en, "context_he": ctx_he}


# ---------------------------------------------------------------------------
# UI JSON writers
# ---------------------------------------------------------------------------

def write_ui_json(
    current_7: dict, similarities_7: list[dict],
    current_21: dict, similarities_21: list[dict],
    signals: list[dict],
) -> None:
    os.makedirs(UI_DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)

    closest_pre_7, max_pre_7   = _best_pre(similarities_7)
    closest_pre_21, max_pre_21 = _best_pre(similarities_21)
    closest_21, _              = _best_match(similarities_21)
    spike  = max_pre_7 - max_pre_21
    status = _status(max_pre_7)

    narratives = generate_narratives(
        status, max_pre_7, max_pre_21,
        closest_pre_7, closest_21, spike, signals
    )

    # Read previous score for jump detection
    prev_score = None
    if os.path.exists(UI_HISTORY):
        try:
            hist = json.loads(open(UI_HISTORY, encoding="utf-8").read())
            runs = hist.get("runs", [])
            if runs:
                prev_score = runs[-1].get("headline_score_7day")
        except Exception:
            pass

    score_7_pct  = round(max_pre_7  * 100)
    score_21_pct = round(max_pre_21 * 100)
    jump = (score_7_pct - prev_score) if prev_score is not None else None

    latest = {
        "timestamp_utc": now.isoformat(),
        "status": status,
        "headline_score_7day":  score_7_pct,
        "headline_score_21day": score_21_pct,
        "score_jump": jump,
        "closest_pre_period_7day": closest_pre_7,
        "closest_pre_period_label_en": _period_label(closest_pre_7, "en"),
        "closest_pre_period_label_he": _period_label(closest_pre_7, "he"),
        "summary_en": narratives["summary_en"],
        "summary_he": narratives["summary_he"],
        "context_en": narratives["context_en"],
        "context_he": narratives["context_he"],
        "signals": signals,
        "comparison_table_7day":  similarities_7,
        "comparison_table_21day": similarities_21,
        "current_metrics": {
            "window_7d": {k: current_7.get(k) for k in (
                "volume_total","volume_mean_daily","volume_peak","days_active",
                "articles_en","articles_he","articles_fa","confluence_score",
                "unique_domains_total","tone_mean")},
            "window_21d": {k: current_21.get(k) for k in (
                "volume_total","volume_mean_daily","volume_peak","days_active",
                "articles_en","articles_he","articles_fa","confluence_score",
                "unique_domains_total","tone_mean")},
        },
        "data_quality_notes": _quality_notes(current_7, current_21),
    }
    with open(UI_LATEST, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2, ensure_ascii=False)

    # --- history.json ---
    history_entry = {
        "timestamp_utc": now.isoformat(),
        "headline_score_7day":  score_7_pct,
        "headline_score_21day": score_21_pct,
        "status": status,
    }
    hist_data = {"runs": []}
    if os.path.exists(UI_HISTORY):
        try:
            hist_data = json.loads(open(UI_HISTORY, encoding="utf-8").read())
        except Exception:
            pass
    runs = hist_data.get("runs", [])
    runs.append(history_entry)
    if len(runs) > HISTORY_MAX:
        runs = runs[-HISTORY_MAX:]
    with open(UI_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"runs": runs}, f, indent=2, ensure_ascii=False)


_SIGNAL_DIRECTION = {
    "diplomatic_breakdown": "warning",
    "supreme_leader":       "warning",
    "trump_china":          "warning",
    "military_strike":      "warning",
}

_ARCHIVE_REF_LABELS = {
    "PRE_APR24": "אפריל 2024",
    "PRE_OCT24": "אוקטובר 2024",
    "PRE_JUN25": "יוני 2025",
    "PRE_FEB26": "פברואר 2026",
}

_STATUS_HE = {"red": "מחריף", "yellow": "מתוח", "green": "שקט"}
_ARCHIVE_STATUS_HE = {"red": "דמיון גבוה", "yellow": "דמיון גבולי", "green": "דמיון נמוך"}

_DOMAIN_DISPLAY = {
    "ynetnews.com": "Ynet", "haaretz.com": "הארץ", "n12.co.il": "N12",
    "walla.co.il": "וואלה", "mako.co.il": "מאקו", "timesofisrael.com": "ToI",
    "jpost.com": "J.Post", "reuters.com": "Reuters", "nytimes.com": "NYT",
    "bbc.com": "BBC", "bbc.co.uk": "BBC", "aljazeera.com": "Al Jazeera",
    "aljazeera.net": "Al Jazeera", "tehrantimes.com": "Tehran Times",
    "ft.com": "FT", "apnews.com": "AP", "theguardian.com": "Guardian",
}


def _parse_time_he(seendate: str) -> str:
    """Extract HH:MM from GDELT seendate (YYYYMMDDHHMMSS or YYYYMMDDTHHMMSSZ)."""
    try:
        clean = seendate.replace("T", "").replace("Z", "")
        if len(clean) >= 12:
            return clean[8:10] + ":" + clean[10:12]
    except Exception:
        pass
    return ""


def write_data_json(
    current_7: dict, similarities_7: list[dict],
    current_21: dict, similarities_21: list[dict],
    signals: list[dict],
) -> None:
    """Write docs/data/data.json — the feed consumed by the new dashboard (index.html)."""
    os.makedirs(UI_DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)

    _, max_pre_7  = _best_pre(similarities_7)
    _, max_pre_21 = _best_pre(similarities_21)
    score_7  = round(max_pre_7  * 100)
    score_21 = round(max_pre_21 * 100)
    status   = _status(max_pre_7)

    # Delta from most recent history entry
    prev_score = None
    if os.path.exists(UI_HISTORY):
        try:
            hist = json.loads(open(UI_HISTORY, encoding="utf-8").read())
            runs = hist.get("runs", [])
            if runs:
                prev_score = runs[-1].get("headline_score_7day")
        except Exception:
            pass
    delta = (score_7 - prev_score) if prev_score is not None else None

    # Signals
    signals_out = []
    for s in signals:
        count = s.get("count_current")
        ratio_wow = s.get("ratio_wow")
        ratio_mom = s.get("ratio_mom")
        signals_out.append({
            "id":              s["id"],
            "name_he":         s.get("name_he", ""),
            "description_he":  s.get("description_he", ""),
            "direction":       _SIGNAL_DIRECTION.get(s["id"], "warning"),
            "article_count_week": count,
            "ratio_wow":       ratio_wow,
            "ratio_mom":       ratio_mom,
            "intensity":       s.get("intensity", "unknown"),
        })

    # Today events: top 3 most-recent articles, one per signal
    all_articles = []
    for s in signals:
        for a in s.get("articles", []):
            if a.get("title"):
                all_articles.append({
                    "signal_id": s["id"],
                    "title":     a.get("title", ""),
                    "url":       a.get("url", ""),
                    "domain":    a.get("domain", ""),
                    "seendate":  a.get("seendate", ""),
                })
    all_articles.sort(key=lambda a: a.get("seendate", ""), reverse=True)
    seen_sigs: set = set()
    today_events: list = []
    for a in all_articles:
        if a["signal_id"] not in seen_sigs:
            today_events.append({
                "time":           _parse_time_he(a["seendate"]),
                "description_he": a["title"],
                "article_count":  1,
                "url":            a["url"],
                "domain":         a["domain"],
            })
            seen_sigs.add(a["signal_id"])
        if len(today_events) >= 3:
            break

    # Trend from history.json
    hist_runs: list = []
    if os.path.exists(UI_HISTORY):
        try:
            hist_data = json.loads(open(UI_HISTORY, encoding="utf-8").read())
            hist_runs = hist_data.get("runs", [])
        except Exception:
            pass
    week_trend  = [{"date": r["timestamp_utc"][:10], "score": r["headline_score_7day"]}
                   for r in hist_runs[-14:]]
    month_trend = [{"date": r["timestamp_utc"][:10], "score": r["headline_score_7day"]}
                   for r in hist_runs[-60:]]

    # Archive reference labels
    ref_events = [
        _ARCHIVE_REF_LABELS[s["reference_id"]]
        for s in similarities_21
        if s.get("is_pre_round") and s["reference_id"] in _ARCHIVE_REF_LABELS
        and s["composite_score"] >= 0.50
    ]
    if not ref_events:
        ref_events = list(_ARCHIVE_REF_LABELS.values())[:3]

    # Sources from signal articles
    domains: set = set()
    total_articles = 0
    for s in signals:
        for a in s.get("articles", []):
            d = a.get("domain", "")
            if d:
                domains.add(d)
        total_articles += (s.get("count_current") or 0)
    source_labels = [_DOMAIN_DISPLAY.get(d, d) for d in sorted(domains)][:15]

    payload = {
        "updated_at": now.isoformat(),
        "short_term": {
            "score":            score_7,
            "status_he":        _STATUS_HE.get(status, "מתוח"),
            "delta_yesterday":  delta,
            "yesterday_score":  prev_score,
        },
        "archive_comparison": {
            "score":            score_21,
            "status_he":        _ARCHIVE_STATUS_HE.get(_status(max_pre_21), "דמיון גבולי"),
            "reference_events": ref_events,
        },
        "signals":      signals_out,
        "today_events": today_events,
        "trend": {
            "week":  week_trend,
            "month": month_trend,
        },
        "sources": {
            "list":         source_labels,
            "total_count":  len(domains),
            "articles_72h": total_articles,
        },
    }
    out_path = os.path.join(UI_DATA_DIR, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _quality_notes(current_7: dict, current_21: dict) -> list[str]:
    notes = []
    errs7  = current_7.get("errors",  [])
    errs21 = current_21.get("errors", [])
    if errs7 or errs21:
        notes.append(f"Some features missing due to API rate limits ({len(errs7)} errors in 7d, {len(errs21)} in 21d). Scores are provisional.")
    return notes


# ---------------------------------------------------------------------------
# save_run and render_report (existing pipeline, unchanged shape)
# ---------------------------------------------------------------------------

def save_run(current_21: dict, similarities_21: list[dict],
             current_7: dict, similarities_7: list[dict]) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    now   = datetime.now(timezone.utc)
    fname = now.strftime("%Y-%m-%d_%H") + ".json"
    path  = os.path.join(RESULTS_DIR, fname)
    payload = {
        "run_at": now.isoformat(),
        "window_21d": {"current": current_21, "similarities": similarities_21},
        "window_7d":  {"current": current_7,  "similarities": similarities_7},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def render_report(current_21: dict, similarities_21: list[dict],
                  current_7: dict,  similarities_7: list[dict]) -> None:
    os.makedirs(os.path.dirname(LATEST_REPORT), exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    max_pre_21 = max((s["composite_score"] for s in similarities_21 if s.get("is_pre_round")), default=0)
    max_pre_7  = max((s["composite_score"] for s in similarities_7  if s.get("is_pre_round")), default=0)
    spike  = max_pre_7 - max_pre_21
    any_warn = any(s.get("warn") for s in similarities_21 + similarities_7)

    start21 = current_21.get("start", "")[:8]
    end21   = current_21.get("end",   "")[:8]
    start7  = current_7.get("start",  "")[:8]

    lines = [
        "# Iran-Israel Conflict Pattern Detector",
        f"\n**Run:** {now_str}  |  **21-day:** {start21}–{end21}  |  **7-day:** {start7}–{end21}\n",
    ]

    if any_warn:
        lines.append("## Warning — High Similarity to Pre-Conflict Pattern\n")
    elif spike > 0.10:
        lines.append(f"## Short-Window Spike (+{round(spike*100)}%)\n")
    else:
        lines.append(f"## Status: Normal\n")

    lines.append(f"21-day max pre: **{round(max_pre_21*100)}%** | 7-day max pre: **{round(max_pre_7*100)}%** | threshold: {round(WARN_THRESHOLD*100)}%\n")

    for label, sims in [("21-Day", similarities_21), ("7-Day", similarities_7)]:
        lines += [f"### {label} Window\n",
                  "| Reference | Type | Score |",
                  "|-----------|------|-------|"]
        for s in sims:
            alert = " WARNING" if s.get("warn") else ""
            lines.append(f"| {s['reference_id']}{alert} | {s['reference_type']} | {s['composite_score']:.1%} |")
        lines.append("")

    with open(LATEST_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
