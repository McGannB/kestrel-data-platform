"""BUG 1: run this twice. The table should not grow, but it does."""

import json
from pathlib import Path

import pandas as pd

latest = sorted(p for p in Path("data/bronze/forms").iterdir() if p.is_dir())[-1]
rows = [e for page in sorted(latest.glob("page_*.json")) for e in json.loads(page.read_text())["value"]]
batch = pd.json_normalize(rows, sep="_")[["Id", "Entry_Status", "Entry_DateSubmitted"]]

out = Path("data/silver/forms_index.parquet")
if out.exists():
    batch = pd.concat([pd.read_parquet(out), batch])
batch.to_parquet(out, index=False)
print("-> rows in forms_index:", len(batch))
