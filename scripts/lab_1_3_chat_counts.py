"""Lab 1.3 - count things in the chat file with plain Python (no pandas)."""

import csv
import json
from collections import Counter
from pathlib import Path

path = Path("data/raw/chat_transcripts_2025-01_2026-09.jsonl")

chats = []
with path.open(encoding="utf-8") as f:
    for line in f:
        chats.append(json.loads(line)) # one chat per line

print("-> chats:", len(chats))

dispositions = Counter(chat["disposition"] for chat in chats)
print("-> escalated to complaint:", dispositions["Escalated - Complaint"])

by_agent = Counter(chat["agent_id"] for chat in chats)
agent, count = by_agent.most_common(1)[0]
print("-> busiest agent:", agent)
print("-> busiest agent chats:", count)

total_turns = sum(len(chat["turns"]) for chat in chats)
print("-> average turns per chat:", round(total_turns / len(chats), 2))

no_member = [chat for chat in chats if chat["member_number"] is None]
print("-> chats with no member number:", len(no_member))

#write a small csv you can open in Excel
Path("data/gold").mkdir(parents=True, exist_ok=True)
with open("data/gold/agent_chat_counts.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["agent_id", "chats"])
    for agent_id, n in sorted(by_agent.items()):
        writer.writerow([agent_id, n])
print("-> rows written:", len(by_agent))

mobile_chat = Counter(chat["channel"] for chat in chats)
print("-> mobile chats:", mobile_chat["mobile_chat"])