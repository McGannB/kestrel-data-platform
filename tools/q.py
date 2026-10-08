"""Run one SQL query against the warehouse and print the result.

python tools/q.py "select count(*) from staging.stg_core__members"
"""

import sys

import duckdb

if len(sys.argv) < 2:
    raise SystemExit('usage: python tools/q.py "select ..."')
con = duckdb.connect("data/warehouse.duckdb", read_only=True)  # read-only: safe while you explore
print(con.sql(sys.argv[1]))
con.close()
