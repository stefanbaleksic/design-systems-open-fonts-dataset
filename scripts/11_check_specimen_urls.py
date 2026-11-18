"""Check the Google Fonts specimen URL of every family in data/google_families_raw.csv with an HTTP request.
Output: data/specimen_url_checks.csv (one row per URL: status code or error, and the day it was checked).
Network needed. Set SKIP_URL_CHECK=1 to keep the previous file unchanged (for offline rebuilds)."""
import csv, datetime, os, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

FD = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(FD, "data")
OUT = os.path.join(D, "specimen_url_checks.csv")
if os.environ.get("SKIP_URL_CHECK") == "1" and os.path.exists(OUT):
    print("specimen URL check skipped; keeping", os.path.relpath(OUT, FD)); raise SystemExit(0)

rows = list(csv.DictReader(open(os.path.join(D, "google_families_raw.csv"), encoding="utf-8")))
URL = "https://fonts.google.com/specimen/"
urls = sorted({URL + r["family"].replace(" ", "+") for r in rows})  # same rule as script 06
TODAY = datetime.date.today().isoformat()

def check(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "font-dataset-link-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return url, str(resp.status), ""
    except urllib.error.HTTPError as e:
        return url, str(e.code), e.reason
    except Exception as e:  # network or TLS problem: recorded, not hidden
        return url, "error", type(e).__name__

with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(check, urls))

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url", "http_status", "detail", "checked_on"])
    for url, status, detail in results:
        w.writerow([url, status, detail, TODAY])
bad = [r for r in results if r[1] != "200"]
print("specimen URLs:", len(results), "not 200:", len(bad))
for r in bad[:10]:
    print("  ", r)
