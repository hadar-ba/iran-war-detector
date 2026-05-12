"""
Main entry point for the Iran-Israel Conflict Pattern Detector.
Run twice daily by GitHub Actions (cron: 0 0,12 * * *).

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

    # 1. Fetch current period vector
    start, end = get_current_window()
    print(f"Current window: {start[:8]} – {end[:8]}", flush=True)
    current = extract_period("CURRENT", start, end, is_reference=False)

    if current["errors"]:
        print(f"[WARN] {len(current['errors'])} errors during extraction:", flush=True)
        for e in current["errors"]:
            print(f"  - {e}", flush=True)

    # 2. Load reference vectors
    references = load_reference_vectors(REF_DIR)
    if not references:
        print("[ERROR] No reference vectors found in data/reference/ — run stage5 first.", flush=True)
        sys.exit(1)
    print(f"Loaded {len(references)} reference vectors: {', '.join(sorted(references))}", flush=True)

    # 3. Compute similarities
    similarities = rank_similarities(current, references)

    # 4. Print summary
    print("\nSimilarity scores (highest first):")
    for s in similarities:
        warn_tag = " <-- WARNING" if s.get("warn") else ""
        print(f"  {s['reference_id']:15s} {s['composite_score']:.1%}  ({s['reference_type']}){warn_tag}")

    # 5. Save results and render report
    result_path = save_run(current, similarities)
    render_report(current, similarities)
    print(f"\nResults: {result_path}")
    print(f"Report:  {os.path.join(_REPO_ROOT, 'reports', 'latest.md')}", flush=True)

    # Exit 2 if any warnings triggered (for CI visibility)
    if any(s.get("warn") for s in similarities):
        print("\n[!] WARNING: high similarity to pre-conflict pattern detected.", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
