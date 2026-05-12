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


def save_run(current_vector: dict, similarities: list[dict]) -> str:
    """
    Persist results to data/results/YYYY-MM-DD_HH.json.
    Returns the output path.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    fname = now.strftime("%Y-%m-%d_%H") + ".json"
    path = os.path.join(RESULTS_DIR, fname)
    payload = {
        "run_at": now.isoformat(),
        "current_period": current_vector,
        "similarities": similarities,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def render_report(current_vector: dict, similarities: list[dict]) -> None:
    """Write reports/latest.md."""
    os.makedirs(os.path.dirname(LATEST_REPORT), exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    start_disp = current_vector.get("start", "")[:8]
    end_disp = current_vector.get("end", "")[:8]

    warnings = [s for s in similarities if s.get("warn")]
    max_pre = max(
        (s["composite_score"] for s in similarities if s.get("is_pre_round")),
        default=0.0
    )

    lines = [
        "# Iran-Israel Conflict Pattern Detector",
        f"\n**Run:** {now_str}",
        f"**Analysis window:** {start_disp} – {end_disp} (21 days)\n",
    ]

    # Alert banner
    if warnings:
        lines.append("## ⚠️ WARNING — HIGH SIMILARITY TO PRE-CONFLICT PATTERN\n")
        for w in warnings:
            lines.append(
                f"Similarity to **{w['reference_id']}** (pre-round): "
                f"**{w['composite_score']:.1%}** (threshold: {WARN_THRESHOLD:.0%})\n"
            )
    else:
        lines.append(f"## ✅ Status: Normal\n")
        lines.append(f"Max similarity to any pre-round period: **{max_pre:.1%}** (threshold: {WARN_THRESHOLD:.0%})\n")

    # Similarity table
    lines += [
        "## Similarity to Reference Periods\n",
        "| Reference | Type | Score | Volume | Confluence | Lang Balance | Diversity | Tone |",
        "|-----------|------|-------|--------|------------|--------------|-----------|------|",
    ]
    for s in similarities:
        ss = s.get("sub_scores", {})
        alert = " 🚨" if s.get("warn") else ""
        lines.append(
            f"| {s['reference_id']}{alert} | {s['reference_type']} "
            f"| **{s['composite_score']:.1%}** "
            f"| {_fmt(ss.get('raw_volume'))} "
            f"| {_fmt(ss.get('confluence'))} "
            f"| {_fmt(ss.get('cross_lang_correlation'))} "
            f"| {_fmt(ss.get('source_diversity'))} "
            f"| {_fmt(ss.get('tone'))} |"
        )

    # Current period stats
    lines += [
        "\n## Current Period Metrics\n",
        f"- **Volume intensity total:** {current_vector.get('volume_total')}",
        f"- **Days active:** {current_vector.get('days_active')} / 21",
        f"- **Articles sampled:** EN={current_vector.get('articles_en')}  "
        f"HE={current_vector.get('articles_he')}  FA={current_vector.get('articles_fa')}",
        f"- **Cross-language confluence:** {current_vector.get('confluence_score', 0):.1%}",
        f"- **Unique domains (union):** {current_vector.get('unique_domains_total')}",
        f"- **Mean tone:** {current_vector.get('tone_mean')}",
        f"- **Silent signals:** {current_vector.get('silent_signals') or 'not available'}",
    ]

    if current_vector.get("errors"):
        lines.append("\n### Data collection errors")
        for e in current_vector["errors"]:
            lines.append(f"- {e}")

    lines += [
        "\n---",
        "*This report is generated automatically. Similarity score ≠ prediction.*",
        "*Reference: 4 pre-round + 1 post-ceasefire + 1 quiet period.*",
    ]

    with open(LATEST_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _fmt(val) -> str:
    if val is None:
        return "—"
    return f"{val:.1%}"
