"""
Historian: saves run results and renders reports/latest.md.
"""

import json
import os
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(_REPO_ROOT, "data", "results")
LATEST_REPORT = os.path.join(_REPO_ROOT, "reports", "latest.md")

WARN_THRESHOLD = 0.70


def save_run(current_21: dict, similarities_21: list[dict],
             current_7: dict, similarities_7: list[dict]) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    fname = now.strftime("%Y-%m-%d_%H") + ".json"
    path = os.path.join(RESULTS_DIR, fname)
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
    warn_21    = [s for s in similarities_21 if s.get("warn")]
    warn_7     = [s for s in similarities_7  if s.get("warn")]
    any_warn   = warn_21 or warn_7

    start21 = current_21.get("start", "")[:8]
    end21   = current_21.get("end",   "")[:8]
    start7  = current_7.get("start",  "")[:8]

    lines = [
        "# Iran-Israel Conflict Pattern Detector",
        f"\n**Run:** {now_str}  |  **21-day window:** {start21}–{end21}  |  **7-day window:** {start7}–{end21}\n",
    ]

    # Status banner
    if any_warn:
        lines.append("## ⚠️ WARNING — HIGH SIMILARITY TO PRE-CONFLICT PATTERN\n")
        for w in warn_21 + warn_7:
            win = "21d" if w in warn_21 else "7d"
            lines.append(f"[{win}] Similarity to **{w['reference_id']}**: **{w['composite_score']:.1%}** (threshold {WARN_THRESHOLD:.0%})\n")
    elif spike > 0.10:
        lines.append(f"## ⚠️ SHORT-WINDOW SPIKE DETECTED\n")
        lines.append(f"7-day pre-similarity (**{max_pre_7:.1%}**) is {spike:.1%} above 21-day ({max_pre_21:.1%}) — recent acceleration.\n")
    else:
        lines.append(f"## ✅ Status: Normal\n")
        lines.append(f"21-day max pre-round similarity: **{max_pre_21:.1%}** | 7-day: **{max_pre_7:.1%}** (threshold: {WARN_THRESHOLD:.0%})\n")

    # Similarity tables
    lines += ["## Similarity Scores\n", "### 21-Day Window\n",
              "| Reference | Type | Score | Volume | Confluence | Lang Balance | Diversity | Tone |",
              "|-----------|------|-------|--------|------------|--------------|-----------|------|"]
    for s in similarities_21:
        lines.append(_row(s))

    lines += ["\n### 7-Day Window\n",
              "| Reference | Type | Score | Volume | Confluence | Lang Balance | Diversity | Tone |",
              "|-----------|------|-------|--------|------------|--------------|-----------|------|"]
    for s in similarities_7:
        lines.append(_row(s))

    # Current metrics
    def _metrics(vec, label):
        lines.append(f"\n### {label}\n")
        lines.append(f"- **Volume total:** {vec.get('volume_total')}  |  **Mean/day:** {vec.get('volume_mean_daily')}  |  **Peak:** {vec.get('volume_peak')}")
        lines.append(f"- **Days active:** {vec.get('days_active')}")
        lines.append(f"- **Articles:** EN={vec.get('articles_en')}  HE={vec.get('articles_he')}  FA={vec.get('articles_fa')}")
        lines.append(f"- **Confluence:** {vec.get('confluence_score', 0):.1%}  |  **Unique domains:** {vec.get('unique_domains_total')}")
        lines.append(f"- **Mean tone:** {vec.get('tone_mean')}")
        if vec.get("errors"):
            lines.append(f"- **Errors:** {', '.join(vec['errors'])}")

    lines.append("\n## Current Period Metrics")
    _metrics(current_21, "21-Day")
    _metrics(current_7,  "7-Day")

    lines += ["\n---",
              "*Similarity score ≠ prediction. Reference: partial vectors (fill in when rate limits clear).*"]

    with open(LATEST_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _row(s: dict) -> str:
    ss = s.get("sub_scores", {})
    alert = " 🚨" if s.get("warn") else ""
    return (f"| {s['reference_id']}{alert} | {s['reference_type']} "
            f"| **{s['composite_score']:.1%}** "
            f"| {_fmt(ss.get('raw_volume'))} "
            f"| {_fmt(ss.get('confluence'))} "
            f"| {_fmt(ss.get('cross_lang_correlation'))} "
            f"| {_fmt(ss.get('source_diversity'))} "
            f"| {_fmt(ss.get('tone'))} |")


def _fmt(val) -> str:
    return "—" if val is None else f"{val:.1%}"
