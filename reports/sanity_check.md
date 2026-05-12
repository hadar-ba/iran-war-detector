# Stage 1: GDELT Coverage Sanity Check

**Generated:** 2026-05-13 (trimmed to 6 launch periods)
**Query:** `Iran AND Israel`
**Metric:** Volume Intensity (normalized 0–1 scale; not raw article count)
**Threshold:** ≥5 days with non-zero coverage per language/period

> **Note:** Full 11-period run completed 2026-05-12 18:11 UTC. This report retains only
> the 6 periods needed for launch: all 4 PRE + POST_FEB26 + QUIET_JAN26.
> Remaining POST and QUIET periods can be added later.

## ⚠️ Warnings

- PRE_JUN25/persian: volume failed - all retries failed (rate-limit; data exists, retriable)
- PRE_FEB26/hebrew: domains failed - all retries failed (rate-limit; volume OK)
- POST_FEB26/persian: volume failed - all retries failed (rate-limit; data exists, retriable)

## Coverage Summary

| Period | Type | Window | English | Hebrew | Persian |
|--------|------|--------|---------|--------|---------|
| PRE_APR24 | pre-round | Mar 23 – Apr 12, 2024 | ✅ 21d | ✅ 21d | ✅ 21d |
| PRE_OCT24 | pre-round | Sep 10 – Sep 30, 2024 | ✅ 21d | ✅ 21d | ✅ 21d |
| PRE_JUN25 | pre-round | May 23 – Jun 12, 2025 | ✅ 21d | ✅ 21d | ❌ ERR |
| PRE_FEB26 | pre-round | Feb 7 – Feb 27, 2026 | ✅ 21d | ✅ 21d | ✅ 21d |
| POST_FEB26 | post-ceasefire | Apr 15 – May 5, 2026 | ✅ 21d | ✅ 21d | ❌ ERR |
| QUIET_JAN26 | quiet | Jan 1 – Jan 21, 2026 | ✅ 21d | ✅ 21d | ✅ 21d |

## Detailed Results

### PRE_APR24 — Mar 23 – Apr 12, 2024 (pre-round)

**English** ✅
- Volume Intensity total: 10.6688
- Days with non-zero coverage: 21
- Expected sources found in sample: ['bbc.com']
- Top domains (sample of 250 articles):
  - `arabi21.com` (32)
  - `sohu.com` (31)
  - `bbc.com` (5) ⭐
  - `ynet.co.il` (4)
  - `radiofarda.com` (4)

**Hebrew** ✅
- Volume Intensity total: 10.6688
- Days with non-zero coverage: 21
- Expected sources found in sample: ['ynet.co.il']
- Top domains (sample of 250 articles):
  - `arabi21.com` (32)
  - `sohu.com` (31)
  - `ynet.co.il` (4) ⭐
  - `radiofarda.com` (4)

**Persian** ✅
- Volume Intensity total: 10.6688
- Days with non-zero coverage: 21
- Expected sources found in sample: ['radiofarda.com']
- Top domains (sample of 250 articles):
  - `arabi21.com` (32)
  - `sohu.com` (31)
  - `radiofarda.com` (4) ⭐

### PRE_OCT24 — Sep 10 – Sep 30, 2024 (pre-round)

**English** ✅
- Volume Intensity total: 19.4934
- Days with non-zero coverage: 21
- Top domains (sample of 250 articles):
  - `ynet.co.il` (8)
  - `haberler.com` (7)
  - `bhol.co.il` (7)
  - `israelnationalnews.com` (6)
  - `maariv.co.il` (6)
  - `radiofarda.com` (5)

**Hebrew** ✅
- Volume Intensity total: 19.4934
- Days with non-zero coverage: 21
- Expected sources found in sample: ['maariv.co.il', 'ynet.co.il']
- Top domains: `ynet.co.il` (8) ⭐, `maariv.co.il` (6) ⭐, `radiofarda.com` (5)

**Persian** ✅
- Volume Intensity total: 19.4934
- Days with non-zero coverage: 21
- Expected sources found in sample: ['radiofarda.com']
- Top domains: `radiofarda.com` (5) ⭐

### PRE_JUN25 — May 23 – Jun 12, 2025 (pre-round)

**English** ✅
- Volume Intensity total: 5.7363
- Days with non-zero coverage: 21
- Domain sample error: all retries failed (rate-limit)

**Hebrew** ✅
- Volume Intensity total: 5.7363
- Days with non-zero coverage: 21
- Expected sources found in sample: ['maariv.co.il', 'ynet.co.il']
- Top domains: `maariv.co.il` (11) ⭐, `ynet.co.il` (6) ⭐, `kikar.co.il` (6)

**Persian** ❌ FAILED
- Error: all retries failed (rate-limit; retriable)

### PRE_FEB26 — Feb 7 – Feb 27, 2026 (pre-round)

**English** ✅
- Volume Intensity total: 13.0287
- Days with non-zero coverage: 21
- Top domains: `haberler.com` (19), `ynet.co.il` (6), `dw.com` (4)

**Hebrew** ✅
- Volume Intensity total: 13.0287
- Days with non-zero coverage: 21
- Domain sample error: all retries failed (rate-limit; volume OK)

**Persian** ✅
- Volume Intensity total: 13.0287
- Days with non-zero coverage: 21
- Top domains: `haberler.com` (19), `ynet.co.il` (6), `dw.com` (4)

### POST_FEB26 — Apr 15 – May 5, 2026 (post-ceasefire)

**English** ✅
- Volume Intensity total: 41.2486
- Days with non-zero coverage: 21
- Top domains: `ilpost.it` (17), `163.com` (8), `haberler.com` (6), `ynet.co.il` (4)

**Hebrew** ✅
- Volume Intensity total: 41.2486
- Days with non-zero coverage: 21
- Expected sources found in sample: ['ynet.co.il']
- Top domains: `ilpost.it` (17), `ynet.co.il` (4) ⭐

**Persian** ❌ FAILED
- Error: all retries failed (rate-limit; retriable)

### QUIET_JAN26 — Jan 1 – Jan 21, 2026 (quiet)

> ⚠️ Calibration note: volume intensity (14.56) is anomalously high for a "quiet" period.
> This window falls ~5-6 weeks before Operation Lion's Roar (PRE_FEB26 begins Feb 7).
> Treat as a mild-pre-escalation baseline, not deep-quiet. Document in Stage 7 calibration.

**English** ✅
- Volume Intensity total: 14.5602
- Days with non-zero coverage: 21
- Expected sources found in sample: ['jpost.com']
- Top domains: `haberler.com` (16), `parsi.euronews.com` (10), `ynet.co.il` (7), `jpost.com` (7) ⭐

**Hebrew** ✅
- Volume Intensity total: 14.5602
- Days with non-zero coverage: 21
- Expected sources found in sample: ['ynet.co.il']
- Top domains: `haberler.com` (16), `ynet.co.il` (7) ⭐, `jpost.com` (7)

**Persian** ✅
- Volume Intensity total: 14.5602
- Days with non-zero coverage: 21
- Expected sources found in sample: ['radiofarda.com']
- Top domains: `haberler.com` (16), `parsi.euronews.com` (10), `radiofarda.com` (4) ⭐

---
*Stage 1 of the Iran-Israel Conflict Pattern Detector pipeline. 6-period launch set.*
