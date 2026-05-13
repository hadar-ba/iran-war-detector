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
HISTORY_MAX      = 60

# Verbose labels for the internal markdown report
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

# Short names used in the one-sentence headline
PERIOD_NAMES_SHORT = {
    "PRE_APR24": {"he": "הסבב הראשון",       "en": "the first round"},
    "PRE_OCT24": {"he": "סבב אוקטובר 2024",  "en": "the October 2024 round"},
    "PRE_JUN25": {"he": "סבב יוני 2025",     "en": "the June 2025 round"},
    "PRE_FEB26": {"he": "'שאגת הארי'",        "en": "Operation Lion's Roar"},
}

# Full names used in context paragraph
PERIOD_NAMES_FULL = {
    "PRE_APR24": {"he": "הסבב הראשון (אפריל 2024)",          "en": "the first round (April 2024)"},
    "PRE_OCT24": {"he": "סבב אוקטובר 2024",                  "en": "the October 2024 round"},
    "PRE_JUN25": {"he": "סבב יוני 2025",                     "en": "the June 2025 round"},
    "PRE_FEB26": {"he": "מבצע 'שאגת הארי' (פברואר 2026)",    "en": "Operation Lion's Roar (February 2026)"},
}

# Clean, editorial-ready signal names (no jargon, sounds like Israeli news)
SIGNAL_DISPLAY = {
    "diplomatic_breakdown": {"he": "קריסת משא ומתן דיפלומטי", "en": "Diplomatic breakdown"},
    "supreme_leader":       {"he": "הצהרות חמינאי",            "en": "Khamenei statements"},
    "trump_china":          {"he": 'צעדים דיפלומטיים של ארה"ב', "en": "US diplomatic moves"},
    "military_strike":      {"he": "פעילות צבאית באזור",        "en": "Military activity"},
}

_INTENSITY_COLOR = {"high": "red", "elevated": "yellow", "baseline": "green"}


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


def _fmt_signal(sig: dict) -> dict | None:
    """Convert raw signal from signals.py to MVP dashboard format.
    Returns None if count is 0/None or intensity is unknown."""
    count = sig.get("count_current")
    if count is None or count == 0:
        return None
    color = _INTENSITY_COLOR.get(sig.get("intensity", ""))
    if not color:
        return None
    display = SIGNAL_DISPLAY.get(sig["id"], {})
    return {
        "id":             sig["id"],
        "intensity":      color,
        "name_he":        display.get("he") or sig.get("name_he", sig["id"]),
        "name_en":        display.get("en") or sig.get("name_en", sig["id"]),
        "count_this_week": count,
        "baseline_avg":   sig.get("count_baseline_avg", 1),
    }


# ---------------------------------------------------------------------------
# Narrative generation — editorial-style, no jargon
# ---------------------------------------------------------------------------

def generate_narratives(
    status: str,
    max_pre_7: float,
    max_pre_21: float,
    closest_pre_7: str | None,
    signals_ui: list[dict],
) -> dict:
    pct7  = round(max_pre_7  * 100)
    pct21 = round(max_pre_21 * 100)

    short_he = PERIOD_NAMES_SHORT.get(closest_pre_7, {}).get("he", "")
    short_en = PERIOD_NAMES_SHORT.get(closest_pre_7, {}).get("en", "")
    full_he  = PERIOD_NAMES_FULL.get(closest_pre_7,  {}).get("he", "")
    full_en  = PERIOD_NAMES_FULL.get(closest_pre_7,  {}).get("en", "")

    # ── One-sentence headline ─────────────────────────────────────────────────
    if status == "red":
        headline_he = (f"החדשות השבוע מתחילות להידמות לתקופה שלפני {short_he}"
                       if short_he else f"החדשות השבוע דומות ב-{pct7}% לתקופות טרום-עימות")
        headline_en = (f"News this week is starting to resemble the period before {short_en}"
                       if short_en else f"News this week is {pct7}% similar to pre-conflict periods")
    elif status == "yellow":
        headline_he = "החדשות השבוע שונות מהשגרה, אבל לא ברמה של תקופה לפני סבב"
        headline_en = "News this week is unusual, but not at pre-round levels"
    else:
        headline_he = "החדשות השבוע מתנהגות כמו בתקופה רגועה"
        headline_en = "News this week looks like a calm period"

    # ── Context paragraph (2–3 sentences, plain language) ────────────────────
    red_sigs  = [s for s in signals_ui if s["intensity"] == "red"]
    top_sig   = red_sigs[0] if red_sigs else (signals_ui[0] if signals_ui else None)

    if status == "red":
        if top_sig:
            count   = top_sig["count_this_week"]
            base    = max(1, top_sig.get("baseline_avg") or 1)
            mult    = max(2, round(count / base))
            name_he = top_sig["name_he"]
            name_en = top_sig["name_en"]
            target_he = full_he or "תקופות טרום-עימות"
            target_en = full_en or "pre-conflict periods"
            ctx_he = (f"השבוע, כתבות על {name_he} קפצו ל-{count} — "
                      f"פי {mult} מהרמה הרגילה. "
                      f"הדמיון הכולל לתקופה שלפני {target_he} עומד על {pct7}%.")
            ctx_en = (f"This week, coverage of {name_en} jumped to {count} articles — "
                      f"{mult}× above the usual level. "
                      f"Overall similarity to the period before {target_en} stands at {pct7}%.")
        else:
            target_he = full_he or "תקופות טרום-עימות"
            target_en = full_en or "pre-conflict periods"
            ctx_he = (f"דפוסי הכיסוי התקשורתי ב-7 הימים האחרונים דומים מאוד "
                      f"לתקופה שלפני {target_he} ({pct7}%). "
                      f"גם ב-21 הימים האחרונים המגמה גבוהה ({pct21}%).")
            ctx_en = (f"News coverage patterns over the last 7 days closely resemble "
                      f"those before {target_en} ({pct7}%). "
                      f"The 21-day picture is also elevated ({pct21}%).")

    elif status == "yellow":
        if top_sig:
            name_he = top_sig["name_he"]
            name_en = top_sig["name_en"]
            ctx_he = (f"השבוע חל שינוי — כתבות על {name_he} מראות עלייה. "
                      f"עדיין לא ברמת טרום-סבב, אבל כדאי לעקוב. "
                      f"רמת הדמיון הנוכחית: {pct7}%.")
            ctx_en = (f"This week shows a change — coverage of {name_en} is elevated. "
                      f"Not yet at pre-round levels, but worth watching. "
                      f"Current level: {pct7}%.")
        else:
            ctx_he = (f"השבוע החדשות שונות מהרגיל. "
                      f"הדמיון לתקופות טרום-עימות עומד על {pct7}% — "
                      f"גבוה מהרגיל, אבל מתחת לסף האזהרה של 70%.")
            ctx_en = (f"This week's news is diverging from normal. "
                      f"Similarity to pre-conflict periods is at {pct7}% — "
                      f"above average, but below the 70% warning threshold.")
    else:
        ctx_he = "החדשות מתנהגות כרגיל. אין עלייה חריגה בנושאים שבדרך כלל מאותתים על הסלמה."
        ctx_en = "News is behaving normally. No unusual spikes in topics that typically signal escalation."

    return {"headline_he": headline_he, "headline_en": headline_en,
            "context_he":  ctx_he,      "context_en":  ctx_en}


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
    _,             max_pre_21  = _best_pre(similarities_21)
    status = _status(max_pre_7)

    signals_ui = [s for s in (_fmt_signal(sig) for sig in signals) if s is not None]

    narratives = generate_narratives(status, max_pre_7, max_pre_21, closest_pre_7, signals_ui)

    # Load existing history for prev score + trend
    hist_runs = []
    if os.path.exists(UI_HISTORY):
        try:
            hist_runs = json.loads(open(UI_HISTORY, encoding="utf-8").read()).get("runs", [])
        except Exception:
            pass

    score_7_pct  = round(max_pre_7  * 100)
    score_21_pct = round(max_pre_21 * 100)

    # Backward-compat: old entries used headline_score_7day
    prev = hist_runs[-1] if hist_runs else {}
    prev_score = prev.get("score_short") if prev.get("score_short") is not None \
                 else prev.get("headline_score_7day")
    jump = (score_7_pct - prev_score) if prev_score is not None else None

    # Trend — last 14 entries, handle both old and new key names
    trend_14d = []
    for r in hist_runs[-14:]:
        s = r.get("score_short") if r.get("score_short") is not None else r.get("headline_score_7day")
        if s is not None:
            trend_14d.append({"date": r["timestamp_utc"][:10], "score": s})

    latest = {
        "timestamp_utc": now.isoformat(),
        "status":        status,
        "score_short":   score_7_pct,
        "score_long":    score_21_pct,
        "score_jump":    jump,
        "headline_he":   narratives["headline_he"],
        "headline_en":   narratives["headline_en"],
        "context_he":    narratives["context_he"],
        "context_en":    narratives["context_en"],
        "trend_14d":     trend_14d,
        "signals":       signals_ui,
        "data_partial":  bool(current_7.get("errors") or current_21.get("errors")),
    }
    with open(UI_LATEST, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2, ensure_ascii=False)

    # Append to history
    hist_runs.append({
        "timestamp_utc": now.isoformat(),
        "score_short":   score_7_pct,
        "score_long":    score_21_pct,
        "status":        status,
    })
    if len(hist_runs) > HISTORY_MAX:
        hist_runs = hist_runs[-HISTORY_MAX:]
    with open(UI_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"runs": hist_runs}, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# save_run and render_report — unchanged
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
    spike      = max_pre_7 - max_pre_21
    any_warn   = any(s.get("warn") for s in similarities_21 + similarities_7)

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
        lines.append("## Status: Normal\n")

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
