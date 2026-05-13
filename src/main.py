"""
Main entry point — runs twice daily via GitHub Actions.
Produces 21-day and 7-day similarity analyses + public dashboard JSON.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdelt_client import get_current_window
from historian import render_report, save_run, write_ui_json, write_data_json
from period_extractor import extract_period
from signals import detect_signals
from similarity_engine import load_reference_vectors, rank_similarities

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(_REPO_ROOT, "data", "reference")


def main():
    print("Iran-Israel Conflict Pattern Detector", flush=True)

    references = load_reference_vectors(REF_DIR)
    if not references:
        print("[ERROR] No reference vectors — run stage5 first.", flush=True)
        sys.exit(1)
    print(f"Loaded {len(references)} reference vectors: {', '.join(sorted(references))}", flush=True)

    # 21-day window
    start21, end21 = get_current_window(days=21)
    print(f"\n[21d] {start21[:8]} – {end21[:8]}", flush=True)
    current_21 = extract_period("CURRENT_21D", start21, end21, is_reference=False)
    if current_21["errors"]:
        print(f"  [WARN] errors: {current_21['errors']}", flush=True)
    sims_21 = rank_similarities(current_21, references)

    # 7-day window
    start7, end7 = get_current_window(days=7)
    print(f"[7d]  {start7[:8]} – {end7[:8]}", flush=True)
    current_7 = extract_period("CURRENT_7D", start7, end7, is_reference=False)
    if current_7["errors"]:
        print(f"  [WARN] errors: {current_7['errors']}", flush=True)
    sims_7 = rank_similarities(current_7, references)

    # Signal detection (fail-fast on 429 — no blocking)
    print("\n[signals]", flush=True)
    signals = detect_signals(start7, end7)
    for s in signals:
        cnt = s["count_current"] if s["count_current"] is not None else "N/A"
        print(f"  {s['id']:25s} {s['intensity']:8s}  count={cnt}", flush=True)

    # Summary
    max_pre_21 = max((s["composite_score"] for s in sims_21 if s.get("is_pre_round")), default=0)
    max_pre_7  = max((s["composite_score"] for s in sims_7  if s.get("is_pre_round")), default=0)
    spike = max_pre_7 - max_pre_21

    print(f"\n21d similarity: {max_pre_21:.1%}  |  7d: {max_pre_7:.1%}  |  spike: {spike:+.1%}", flush=True)
    if spike > 0.10:
        print(f"[!] SHORT-WINDOW SPIKE", flush=True)
    for s in sims_7:
        tag = " <-- WARNING" if s.get("warn") else ""
        print(f"  [7d] {s['reference_id']:15s} {s['composite_score']:.1%}  ({s['reference_type']}){tag}", flush=True)

    # Persist
    result_path = save_run(current_21, sims_21, current_7, sims_7)
    render_report(current_21, sims_21, current_7, sims_7)
    write_ui_json(current_7, sims_7, current_21, sims_21, signals)
    write_data_json(current_7, sims_7, current_21, sims_21, signals)

    print(f"\nResults: {result_path}", flush=True)
    print(f"UI JSON: docs/data/latest.json + docs/data/history.json", flush=True)

    if any(s.get("warn") for s in sims_21 + sims_7):
        print("\n[!] WARNING: high similarity to pre-conflict pattern.", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
