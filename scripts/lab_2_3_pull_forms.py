"""Lab 2.3 - pull every page of the OData feed into bronze, exactly as received."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("FORMS_TOKEN")

run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out_dir = Path("data/bronze/forms") / run_id
out_dir.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers["Authorization"] = f"Bearer {TOKEN}"

url = f"{BASE}/odata/Forms(12)/Entries"
params = {"$top": 100, "$count": "true"}
page_no, total_entries, expected = 0, 0, None

while url:
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status() # stop loudly on 4xx/5xx
    body = response.json()
    page_no += 1
    if expected is None:
        expected = body.get("@odata.count")
    (out_dir / f"page_{page_no:04d}.json").write_text(json.dumps(body), encodings="utf-8")
    total_entries += len(body["value"])
    url = body.get("@odata.nextLink") # None on the last page -> loop ends
    params = None # the nextLink already has all the params

manifest = {
    "run_id": run_id,
    "source": "FormsHub OData",
    "pages": page_no,
    "entries": total_entries,
    "expected": expected,
    "finished_at": datetime.now(timezone.utc).isoformat(),
}
(out_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("-> pages saved:", page_no)
print("-> entries pulled:", total_entries)
print("-> matches @odata.count:", "yes" if total_entries == expected else "NO")

incomplete = 0
for page in sorted(out_dir.glob("page_*.json")):
    for entry in json.loads(page.read_text(encodings="utf-8"))["value"]:
        if entry["Entry"]["Status"] == "Incomplete":
            incomplete += 1
print("-> incomplete entries:", incomplete)