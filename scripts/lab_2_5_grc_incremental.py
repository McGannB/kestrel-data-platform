"""Lab 2.5 - incremental loads from the GRC table API using a watermark.

First run: pulls everything. Later runs: only rows changed since the last run.
Every version we pull is appended to a change log (bronze); a "current" table keeps
the latest version of each issue (upsert by sys_id).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
AUTH = (os.getenv("GRC_USER"), os.getenv("GRC_PASSWORD"))

state_file = Path("data/state/grc_watermark.json")
changes_file = Path("data/bronze/grc/grc_issue_changes.parquet")
current_file = Path("data/bronze/grc/grc_issues_current.parquet")
for p in (state_file, changes_file):
    p.parent.mkdir(parents=True, exist_ok=True)

watermark = json.loads(state_file.read_text())["sys_updated_on"] if state_file.exists() else None
query = "ORDERBYsys_updated_on"
if watermark:
    query = f"sys_updated_on>{watermark}^ORDERBYsys_updated_on"
print("watermark:", watermark or "(none - full load)")

url = f"{BASE}/api/now/table/grc_issue"
params = {
    "sysparm_query": query,
    "sysparm_limit": 100,
    "sysparm_display_value": "false",
    "sysparm_exclude_reference_link": "true",
}
rows, pages = [], 0
while url:
    r = requests.get(url, params=params, auth=AUTH, timeout=30)
    r.raise_for_status()
    pages += 1
    rows.extend(r.json()["result"])
    url = r.links.get("next", {}).get("url")  # requests reads the Link header for you
    params = None

print("-> rows pulled this run:", len(rows))
print("-> pages this run:", pages)
if not rows:
    print("-> nothing new since the last run")
    raise SystemExit(0)  # not an error: a quiet day is normal

batch = pd.DataFrame(rows)
batch["assigned_to"] = batch["assigned_to"].map(lambda v: v.get("value") if isinstance(v, dict) else v)
batch["_pulled_at"] = datetime.now(timezone.utc).isoformat()

# 1) append every version to the change log (never lose history)
changes = pd.concat([pd.read_parquet(changes_file), batch]) if changes_file.exists() else batch
changes.to_parquet(changes_file, index=False)

# 2) upsert: keep only the newest version of each issue
current = changes.sort_values("sys_updated_on").drop_duplicates("sys_id", keep="last")
current.to_parquet(current_file, index=False)

# 3) move the watermark forward only after both writes worked
new_mark = batch["sys_updated_on"].max()
state_file.write_text(json.dumps({"sys_updated_on": new_mark}))
print("-> change log rows:", len(changes))
print("-> current issues:", len(current))
print("-> open issues:", int((current["active"] == "true").sum()))