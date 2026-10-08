"""Lab 13.2 - this report is correct but SLOW. Make it at least 10x faster without changing the output."""

import time

import pandas as pd

t0 = time.perf_counter()
complaints = pd.read_parquet("data/silver/complaints.parquet")
rows = []
for _, c in complaints.iterrows():  # row-by-row loop
    members = pd.read_csv("data/raw/members_extract_20260930.txt", sep="|")  # re-reads the whole file for EVERY row
    match = members[members["member_number"] == c["member_number"]]
    if len(match) == 0:
        continue
    m = match.iloc[0]
    same_member = complaints[complaints["member_number"] == c["member_number"]]
    rows.append(
        {
            "complaint_id": c["complaint_id"],
            "branch_code": m["branch_code"],
            "age": 2026 - m["birth_year"],
            "member_total_complaints": len(same_member),
        }
    )
report = pd.DataFrame(rows).sort_values("complaint_id").reset_index(drop=True)
report.to_csv("data/gold/member_complaint_report.csv", index=False)
print("-> rows:", len(report))
print(
    "-> complaints from members with 3+ complaints:",
    report.loc[report["member_total_complaints"] >= 3, "complaint_id"].count(),
)
print(f"-> seconds: {time.perf_counter() - t0:.1f}")
