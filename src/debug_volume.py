import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdelt_client import _cache_key, CACHE_DIR, BASE_QUERY

# Check 21-day current window volume breakdown
params = {"query": BASE_QUERY, "mode": "timelinevol", "format": "json",
          "startdatetime": "20260422073939", "enddatetime": "20260513073939"}
key = _cache_key(params)
path = os.path.join(CACHE_DIR, key + ".json")
print("cache exists:", os.path.exists(path))
if os.path.exists(path):
    data = json.load(open(path))["data"]
    print(f"days: {len(data)}")
    total = sum(e["value"] for e in data)
    last7 = sum(e["value"] for e in data if e["date"][:8] >= "20260506")
    print(f"total vol: {total:.4f}  last-7d vol: {last7:.4f}  ratio: {last7/total:.1%}")
    print()
    for e in data[-14:]:  # show last 14 days
        bar = "#" * int(e["value"] * 30)
        print(f"  {e['date'][:10]}  {e['value']:.4f}  {bar}")
