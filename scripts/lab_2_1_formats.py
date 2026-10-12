"""Lab 2.1 - read every kind of file the kit has, and save Parquet."""

from pathlib import Path
import pandas as pd

raw = Path("data/raw")
bronze = Path("data/bronze")
bronze.mkdir(parents=True, exist_ok=True)

# 1. Pipe-delimited text file from the core banking system
members = pd.read_csv(raw / "members_extract_20260930.txt", sep="|", dtype={"zip": "string"}, parse_dates=["join_date"])
print("-> members rows:", len(members))
print("-> members columns:", len(members.columns))

# 2. A CSV saved by an old Windows program (cp1252 encoding, not UTF-8)
try:
    cards = pd.read_csv(raw / "branch_comment_cards_2026.csv")
except UnicodeDecodeError as err:
    print("Utf-8 failed:", err.reason)
    cards = pd.read_csv(raw / "branch_comment_cards_2026.csv", encoding="cp1252")
print("-> comment cards:", len(cards))
print("-> cards mentioning José:", int(cards["comment"].str.contains("José").sum()))

# 3. Excel workbook with two sheets
sheets = pd.ExcelFile(raw / "RegE_Dispute_Log_2025-2026.xlsx").sheet_names
print("-> excel sheets:", ", ".join(sheets))

# 4. JSON Lines (one JSON object per line)
chats = pd.read_json(raw / "chat_transcripts_2025-01_2026-09.jsonl", lines=True, dtype={"member_number": "string"})
print("-> chats rows:", len(chats))

# 5. Save members as Parquet and compare sizes
out = bronze / "members.parquet"
members.to_parquet(out, index=False)
csv_kb = (raw / "members_extract_20260930.txt").stat().st_size / 1024
pq_kb = out.stat().st_size / 1024
print("-> csv KB:", round(csv_kb))
print("-> parquet smaller than csv:", "yes" if pq_kb < csv_kb else "no")
back = pd.read_parquet(out)
print(
    "-> join_date is still a date after reload:",
    "yes" if pd.api.types.is_datetime64_any_dtype(back["join_date"]) else "no",
)