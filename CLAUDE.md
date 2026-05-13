# CLAUDE.md — Internal Notes for Claude Code Sessions

## Project purpose

Quantitative similarity analysis between current 21-day news periods and historical reference periods preceding direct Iran-Israel military exchanges. Output is a similarity score, not a prediction.

## Communication rules

- **Reply to the user in Hebrew** in the chat interface.
- **All code, comments, commits, and repo documentation in English.**

## Architecture overview

- **Data source:** GDELT DOC API (`api.gdeltproject.org/api/v2/doc/doc`) — free, no key
- **Scheduling:** GitHub Actions, cron `0 0,12 * * *` (twice daily UTC)
- **Source modules:** `src/gdelt_client.py`, `src/period_extractor.py`, `src/similarity_engine.py`, `src/historian.py`, `src/main.py`
- **Outputs:** `data/results/YYYY-MM-DD_HH.json` (timestamped), `reports/latest.md` (overwritten each run)

## Critical rules

1. **Never regenerate reference period vectors** (`data/reference/*.json`) unless the user explicitly requests it. They are computed once in Stage 5 and GDELT data for past dates is immutable.
2. **Cache discipline:** Reference queries cached forever. Current-period queries cached 6 hours. Cache key = hash of all query parameters. Cache lives in `data/cache/` (gitignored).
3. **No fabricated data.** If a query returns 0 results or unexpected results, log and report it honestly. Do not fill in expected values.
4. **No secrets in repo.** This is a public repository. No API keys, tokens, or personal information. (GDELT requires no key.)
5. **Ask before architectural decisions.** When facing ambiguity (sparse language coverage, unexpected signal behavior, threshold questions), ask the user.

## Reference periods

| ID | Window | Type |
|----|--------|------|
| PRE_APR24 | Mar 23 – Apr 12, 2024 | Pre-round |
| PRE_OCT24 | Sep 10 – Sep 30, 2024 | Pre-round |
| PRE_JUN25 | May 23 – Jun 12, 2025 | Pre-round |
| PRE_FEB26 | Feb 7 – Feb 27, 2026 | Pre-round |
| POST_APR24 | May 1 – May 21, 2024 | Post-ceasefire |
| POST_OCT24 | Nov 1 – Nov 21, 2024 | Post-ceasefire |
| POST_JUN25 | Jul 1 – Jul 21, 2025 | Post-ceasefire |
| POST_FEB26 | Apr 15 – May 5, 2026 | Post-ceasefire |
| QUIET_FEB25 | Feb 14 – Feb 28, 2025 | Quiet |
| QUIET_SEP25 | Sep 1 – Sep 21, 2025 | Quiet |
| QUIET_JAN26 | Jan 1 – Jan 21, 2026 | Quiet |

## Feature weights (provisional, calibrated in Stage 7)

| Category | Weight |
|----------|--------|
| Silent signals (OSINT) | 40% |
| Cross-language confluence | 25% |
| Cross-language correlation | 10% |
| Raw volume | 10% |
| Source diversity | 10% |
| Tone | 5% |

## Warning threshold

Similarity to any `PRE_*` period > **70%** → prominent warning in report. Provisional; revisit after Stage 7 calibration.

## Launch set (3 periods — minimum viable)

PRE_FEB26, POST_FEB26, QUIET_JAN26.
PRE_APR24, PRE_OCT24, PRE_JUN25 added next (one per day, rate-limit permitting).
Remaining 5 (POST_APR24, POST_OCT24, POST_JUN25, QUIET_FEB25, QUIET_SEP25) after that.

## Implementation stages

| Stage | Description | Status |
|-------|-------------|--------|
| 0 | Infrastructure setup | ✅ Done |
| 1 | GDELT coverage sanity check | ✅ Done (6-period launch set) |
| 2 | Volume timelines | ⏭ Skipped (generated as part of analysis output) |
| 3 | `gdelt_client.py` | Pending |
| 4 | `period_extractor.py` | Pending |
| 5 | Compute reference vectors (6 periods) | Pending |
| 6 | `similarity_engine.py` | Pending |
| 7 | Calibration | ⏭ Skipped (use spec weights) |
| 8 | GitHub Actions workflow | Pending |
| 9 | First real run | Pending |

## Open questions (see spec §12)

1. Hebrew query construction: vocalized vs. non-vocalized, full vs. defective spelling — test empirically in Stage 1.
2. Persian source classification: state media (Tasnim, Fars, IRNA) vs. opposition (Iran International, BBC Persian, Radio Farda) — tag separately in Stage 5.
3. `POST_FEB26` has only one example; document statistical limitation in all reports.
4. Confluence threshold: what counts as "signal appeared in language X today"? Define in Stage 4.
5. Source weighting: currently equal; consider domain trust scoring in v2.
6. Warning threshold: finalize after Stage 7 calibration.

## GDELT API quick reference

```
Base: https://api.gdeltproject.org/api/v2/doc/doc
Modes: timelinevol | timelinetone | artlist | domain
Date format: YYYYMMDDHHMMSS
Languages: english | hebrew | persian
Rate limit: ~1 req/sec (be respectful, no published limit)
artlist cap: 250 results per query
```
