"""Lab 1.5 - read a file that has bad lines, without crashing, and log what happened."""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("logs/lab_1_5.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("lab_1_5")

path = Path(os.getenv("SAMPLE_CHAT_FILE", "labs/lab_1_5/chats_sample_with_errors.jsonl"))
log.info("reading %s", path)

good, bad, blank, missing_member = [], 0, 0, 0
with path.open(encoding="utf-8") as f:
    for line_no, line in enumerate(f, start=1):
        if not line.strip():
            blank += 1
            continue
        try:
            chat = json.loads(line)
        except json.JSONDecodeError as err:
            bad += 1
            log.warning("line %s is not valid JSON (%s) - skipped", line_no, err.msg)
            continue
        if chat.get("member_number") is None:
            missing_member += 1
            log.warning("chat %s has no member number", chat["chat_id"])
        good.append(chat)

log.info("done: %s good, %s bad, %s blank", len(good), bad, blank)
print("-> good chats:", len(good))
print("-> bad lines skipped:", bad)
print("-> blank lines skipped:", blank)
print("-> warnings for missing member number:", missing_member)