"""Run a .sql file against the course warehouse and print every result.

Usage:   python tools/runsql.py sql/lab_5_1_basics.sql
         python tools/runsql.py sql/lab_5_1_basics.sql --db data/warehouse.duckdb

Statements are split on semicolons at the end of a line.
A comment line like   -- check: complaints in total   right above a query prints
"-> complaints in total: <first value of the first row>" so you can compare with the lab.
"""

import argparse
import re
import sys
import time
from pathlib import Path

import duckdb

ap = argparse.ArgumentParser()
ap.add_argument("sql_file")
ap.add_argument("--db", default="data/warehouse.duckdb")
ap.add_argument("--rows", type=int, default=15, help="max rows to print per result")
a = ap.parse_args()

text = Path(a.sql_file).read_text(encoding="utf-8")
statements = [s.strip() for s in re.split(r";\s*$", text, flags=re.M) if s.strip()]
con = duckdb.connect(a.db)

for stmt in statements:
    body = "\n".join(line for line in stmt.splitlines() if not line.strip().startswith("--")).strip()
    if not body:
        continue
    check = re.search(r"^\s*--\s*check:\s*(.+)$", stmt, re.M)
    comments = [line.strip()[2:].strip() for line in stmt.splitlines() if line.strip().startswith("--")]
    title = next((c for c in comments if not c.lower().startswith("check:")), body.splitlines()[0][:70])
    print(f"\n=== {title}")
    t = time.perf_counter()
    try:
        rel = con.sql(body)
    except duckdb.Error as err:
        print(f"ERROR: {err}")
        sys.exit(1)
    ms = (time.perf_counter() - t) * 1000
    if rel is None:
        print(f"(done in {ms:.0f} ms)")
        continue
    df = rel.df()
    print(df.head(a.rows).to_string(index=False, max_colwidth=60))
    if len(df) > a.rows:
        print(f"... {len(df) - a.rows} more rows")
    print(f"({len(df)} rows, {ms:.0f} ms)")
    if check and len(df):
        print(f"-> {check.group(1).strip()}: {df.iloc[0, 0]}")
con.close()
