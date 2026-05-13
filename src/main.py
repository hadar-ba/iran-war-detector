"""
Main entry point for the Iran-Israel Conflict Pattern Detector.
Run twice daily by GitHub Actions (cron: 0 0,12 * * *).

Produces two parallel analyses:
  - 21-day window: baseline trend comparison
  - 7-day window: short-window spike detection (recent signal emphasis)

A spike in 7-day similarity when 21-day is calm is itself a warning signal.

Usage:
    python src/main.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdelt_client import get_current_window
from historian import render_report, save_run
from period_extractor import extract_period
from similarity_engine import load_reference_vectors, rank_similarities

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(_REPO_ROOT, "data", "reference")


def main():
    print("Iran-Israel Conflict Pattern Detector — starting run", flush=True)

    references = load_reference_vectors(REF_DIR)
    if not references:
        print("[ERROR] No reference vectors found in data/reference/ — run stage5 first.", flush=True)
        sys.exit(1)
    print(f"Loaded {len(references)} reference vectors: {', '.join(sorted(references))}", flush=True)

    # --- 21-day window ---
    start21, end21 = get_current_window(days=21)
    print(f"\n[21-day] {start21[:8]} – {end21[:8]}", flush=True)
    current_21 = extract_period("CURRENT_21D", start21, end21, is_reference=False)
    if current_21["errors"]:
        print(f"  [WARN] {len(current_21['errors'])} errors: {current_21['errors']}", flush=True)
    similarities_21 = rank_similarities(current_21, references)

    # --- 7-day window ---
    start7, end7 = get_current_window(days=7)
    print(f"\n[7-day]  {start7[:8]} – {end7[:8]}", flush=True)
    current_7 = extract_period("CURRENT_7D", start7, end7, is_reference=False)
    if current_7["errors"]:
        print(f"  [WARN] {len(current_7['errors'])} errors: {current_7['errors']}", flush=True)
    similarities_7 = rank_similarities(current_7, references)

    # --- Print summary ---
    print("\n21-day similarity (highest first):")
    for s in similarities_21:
        tag = " <-- WARNING" if s.get("warn") else ""
        print(f"  {s['reference_id']:15s} {s['composite_score']:.1%}  ({s['reference_type']}){tag}")

    print("\n7-day similarity (highest first):")
    for s in similarities_7:
        tag = " <-- WARNING" if s.get("warn") else ""
        print(f"  {s['reference_id']:15s} {s['composite_score']:.1%}  ({s['reference_type']}){tag}")

    # Detect short-window spike: 7d pre similarity is much higher than 21d
    max_pre_21 = max((s["composite_score"] for s in similarities_21 if s.get("is_pre_round")), default=0)
    max_pre_7  = max((s["composite_score"] for s in similarities_7  if s.get("is_pre_round")), default=0)
    spike = max_pre_7 - max_pre_21
    if spike > 0.10:
        print(f"\n[!] SHORT-WINDOW SPIKE: 7d pre-similarity ({max_pre_7:.1%}) is {spike:.1%} above 21d ({max_pre_21:.1%})", flush=True)

    # --- Save and render ---
    result_path = save_run(current_21, similarities_21, current_7, similarities_7)
    render_report(current_21, similarities_21, current_7, similarities_7)
    print(f"\nResults: {result_path}")
    print(f"Report:  {os.path.join(_REPO_ROOT, 'reports', 'latest.md')}", flush=True)

    warn_any = any(s.get("warn") for s in similarities_21 + similarities_7)
    if warn_any:
        print("\n[!] WARNING: high similarity to pre-conflict pattern detected.", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
