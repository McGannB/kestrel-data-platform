"""BUG 2: the team says March 31 2026 had more complaints than this report shows."""

import pandas as pd

c = pd.read_parquet("data/silver/complaints.parquet")
c["day"] = c["submitted_at_utc"].astype(str).str[:10]  # take the date part
per_day = c.groupby("day").size()
print("-> complaints on 2026-03-31:", int(per_day.get("2026-03-31", 0)))
