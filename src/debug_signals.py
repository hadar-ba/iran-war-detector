"""Quick manual signal check — last 7 days."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
START = "20260506000000"
END   = "20260513235959"

SIGNALS = {
    "diplomatic_breakdown": "Iran AND Israel AND (diplomacy OR ceasefire OR deadline OR ultimatum OR negotiations)",
    "supreme_leader":       "Iran AND Khamenei AND Israel",
    "trump_china":          "Iran AND Israel AND Trump AND China",
    "military_strike":      "Iran AND Israel AND (strike OR attack OR missile OR escalation)",
}

def query(name, q):
    params = {"query": q, "mode": "artlist", "format": "json",
              "startdatetime": START, "enddatetime": END,
              "sourcelang": "english", "maxrecords": "50"}
    try:
        r = requests.get(BASE, params=params, timeout=20)
        if r.status_code == 429:
            print(f"  {name:30s}  [429 rate-limited]")
            return
        r.raise_for_status()
        arts = r.json().get("articles", [])
        print(f"  {name:30s}  {len(arts):3d} articles")
        for a in arts[:3]:
            print(f"    - {a.get('title','')[:80]}")
    except Exception as e:
        print(f"  {name:30s}  [ERR: {e}]")
    time.sleep(15)

print(f"Signal check — May 6-13, 2026\n")
for name, q in SIGNALS.items():
    query(name, q)
