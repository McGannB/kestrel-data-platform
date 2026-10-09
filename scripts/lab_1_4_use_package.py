"""Lab 1.4 - use your own package."""

from pathlib import Path

from kvcu.cleaning import normalize_member_number

raw_values = Path("labs/lab_1_4/member_numbers_sample.txt").read_text(encoding="utf-8").splitlines()
clean = [normalize_member_number(v) for v in raw_values]
valid = [n for n in clean if n is not None]

print("-> raw values:", len(raw_values))
print("-> valid member numbers:", len(valid))
print("-> sum of valid numbers:", sum(valid))