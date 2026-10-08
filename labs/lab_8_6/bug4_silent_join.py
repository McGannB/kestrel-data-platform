"""BUG 4: compliance asked how many complaints came from members aged 62+. The answer cannot be zero."""

import pandas as pd

complaints = pd.read_parquet("data/silver/complaints.parquet")
members = pd.read_csv("data/raw/members_extract_20260930.txt", sep="|", dtype=str)  # read everything as text
complaints["member_number"] = (
    complaints["member_number"].astype("string").str.zfill(8)
)  # match the form's 8-digit style
joined = complaints.merge(members, on="member_number", how="inner")
joined["age"] = 2026 - joined["birth_year"].astype(int)
print("-> complaints from members aged 62+:", int((joined["age"] >= 62).sum()))
