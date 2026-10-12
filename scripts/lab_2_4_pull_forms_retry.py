"""Lab 2.4 - the same pull, but it survives 429s, 5xx errors and slow responses."""

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("FORMS_TOKEN")
RETRY_STATUS = {429, 500, 502, 503, 504}
retries = 0

def get_with_retry(session, url, params=None, max_attempts=5, timeout=5):
    """GET with retries. Waits longer after each failure (exponential backoff)."""
    global retries
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as err:
            reason = type(err).__name__
        else:
            if response.status_code not in RETRY_STATUS:
                response.raise_for_status() # 400/401/404: retrying will not help
                return response
            reason = f"HTTP {response.status_code}"
            if response.status_code == 429 and "Retry-After" in response.headers:
                wait = float(response.headers["Retry-After"])
            else:
                wait = None
        if attempt == max_attempts:
            raise RuntimeError(f"gave up after {max_attempts} attempts: {reason}")
        retries += 1
        if reason.startswith("HTTP 429") and wait is not None:
            sleep_for = wait
        else:
            sleep_for = min(30, 0.5 * 2 ** (attempt - 1)) + random.uniform(0, 0.25) # backoff + jitter
        print(f"   retry {retries}: {reason}, waiting {sleep_for:.1f}s")
        time.sleep(sleep_for)


run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out_dir = Path("data/bronze/forms") / run_id
out_dir.mkdir(parents=True, exist_ok=True)
session = requests.Session()
session.headers["Authorization"] = f"Bearer {TOKEN}"

url, params = f"{BASE}/odata/Forms(12)/Entries", {"$top": 100, "$count": "true"}
page_no, total, expected = 0, 0, None
while url:
    body = get_with_retry(session, url, params).json()
    page_no += 1
    expected = expected or body.get("@odata.count")
    (out_dir / f"page_{page_no:04d}.json").write_text(json.dumps(body), encoding="utf-8")
    total += len(body["value"])
    url, params = body.get("@odata.nextLink"), None

(out_dir / "_manifest.json").write_text(
    json.dumps({"run_id": run_id, "pages": page_no, "entries":total, "retries": retries}), encoding="utf-8"
)
print("-> entries pulled:", total)
print("-> retries needed:", retries)
print("-> matches @odata.count:", "yes" if total == expected else "NO")