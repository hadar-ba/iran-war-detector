# Iran-Israel Conflict Pattern Detector

A quantitative tool that analyzes global news coverage (English, Hebrew, and Persian) and compares the current period against historical reference periods to estimate how similar the current period is to those preceding direct Iran-Israel military exchanges.

## What this tool does

The tool builds a *holistic description* of each 21-day news period using features derived from the [GDELT Document 2.0 API](https://api.gdeltproject.org/api/v2/doc/doc), then computes a weighted similarity score against a library of reference periods. The unit of analysis is the period as a whole — not individual headlines — following the logic of a historian examining thousands of documents in aggregate.

**This tool outputs similarity to historical patterns. It does not predict events.**

## Feature categories

| Category | Weight | Description |
|----------|--------|-------------|
| Silent signals (OSINT-style) | 40% | Diplomatic breakdowns, military exercises, reserve call-ups, airspace closures, operational language, etc. |
| Cross-language confluence | 25% | Events appearing independently across English, Hebrew, and Persian sources within the same time window |
| Cross-language correlation | 10% | Signal strength consistency across language ecosystems |
| Raw volume | 10% | Article counts and trends per language |
| Source diversity | 10% | Domain breadth and concentration (Herfindahl index) |
| Tone | 5% | Mean sentiment and negative-ratio per language |

## Reference periods

The tool is calibrated against 11 reference periods:

- **Pre-round (4 periods):** 21-day windows preceding direct Iranian missile attacks on Israel (April 2024, October 2024, June 2025, February 2026)
- **Post-ceasefire (4 periods):** Windows following each ceasefire, representing the baseline from which the next round might emerge
- **Quiet (3 periods):** Periods with no significant military activity, used as negative examples

## Data source

All data comes from the GDELT Document 2.0 API — free, no registration or API key required.

## Limitations

- Coverage is limited to sources indexed by GDELT; not all news domains are included.
- Analysis runs twice daily (00:00 and 12:00 UTC) via GitHub Actions.
- The similarity score is one quantitative input among many and is not a substitute for human judgment.
- Statistical power is limited: the reference library contains a small number of examples.

## Latest report

The latest analysis is in [`reports/latest.md`](reports/latest.md).

## Running locally

```bash
pip install -r requirements.txt
python src/main.py
```

## License

MIT
