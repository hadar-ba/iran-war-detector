"""
Stage 5: Compute and persist reference vectors for the 6 launch periods.
Saves to data/reference/{period_id}.json.

Per CLAUDE.md rule: never regenerate reference vectors unless explicitly requested.
These JSON files are the ground truth; git-committed and never overwritten by the pipeline.

Run from repo root:
    $env:PYTHONUTF8=1; python src/stage5_compute_references.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from period_extractor import extract_period

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(REPO_ROOT, "data", "reference")

LAUNCH_PERIODS = {
    # Minimum viable set for launch — other periods added incrementally
    "PRE_FEB26":  ("20260207000000", "20260227235959"),
    "POST_FEB26": ("20260415000000", "20260505235959"),
    "QUIET_JAN26":("20260101000000", "20260121235959"),
}


def main():
    os.makedirs(REF_DIR, exist_ok=True)
    print(f"Stage 5: computing {len(LAUNCH_PERIODS)} reference vectors")
    print(f"Output: {REF_DIR}\n")

    results = {}
    for period_id, (start, end) in LAUNCH_PERIODS.items():
        out_path = os.path.join(REF_DIR, f"{period_id}.json")
        if os.path.exists(out_path):
            print(f"[SKIP] {period_id} — already exists ({out_path})")
            with open(out_path, encoding="utf-8") as f:
                results[period_id] = json.load(f)
            continue

        print(f"[EXTRACT] {period_id}  {start[:8]} - {end[:8]} ...", flush=True)
        vec = extract_period(period_id, start, end, is_reference=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(vec, f, indent=2, ensure_ascii=False)

        status = "[ERR]" if vec["errors"] else "[OK]"
        print(f"  {status} vol={vec['volume_total']} confluence={vec['confluence_score']} "
              f"domains={vec['unique_domains_total']} errors={vec['errors']}", flush=True)
        results[period_id] = vec

    # Summary
    print("\n=== Summary ===")
    for pid, vec in results.items():
        errs = vec.get("errors", [])
        flag = "WARN" if errs else "OK"
        print(f"  [{flag}] {pid}: vol={vec['volume_total']} "
              f"en={vec['articles_en']} he={vec['articles_he']} fa={vec['articles_fa']} "
              f"confluence={vec['confluence_score']} domains={vec['unique_domains_total']}")
        for e in errs:
            print(f"         ! {e}")

    print(f"\nReference vectors saved to: {REF_DIR}")


if __name__ == "__main__":
    main()
