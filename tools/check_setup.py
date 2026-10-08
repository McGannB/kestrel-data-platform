"""Lab 0.1 - check that your workbench is ready.

Run from the kit folder:   python tools/check_setup.py
"""

import importlib
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok = True

print(f"Python {platform.python_version()} on {platform.system()}")
if sys.version_info < (3, 11):
    print("  !! Python 3.11 or newer is needed (3.13 recommended).")
    ok = False

if sys.prefix == sys.base_prefix:
    print("  !! You are NOT inside a virtual environment. Activate .venv first (see Lab 0.1, step 4).")
    ok = False
else:
    print(f"  virtual environment: {Path(sys.prefix).name}")

for pkg in [
    "pandas",
    "pyarrow",
    "polars",
    "duckdb",
    "requests",
    "openpyxl",
    "fastapi",
    "strawberry",
    "rapidfuzz",
    "pypdf",
    "sklearn",
    "pytest",
]:
    try:
        m = importlib.import_module(pkg)
        print(f"  ok  {pkg:12} {getattr(m, '__version__', '')}")
    except Exception as e:  # noqa: BLE001
        print(f"  !!  {pkg:12} missing ({e.__class__.__name__}). Run: python -m pip install -r requirements.txt")
        ok = False

raw = ROOT / "data" / "raw"
files = sorted(p for p in raw.iterdir() if p.is_file()) if raw.exists() else []
pdfs = sorted((raw / "policies").glob("*.pdf")) if raw.exists() else []
if not files:
    print("  !! data/raw is empty or missing. Run this from the unzipped kit folder.")
    ok = False

print()
print("-> raw data files:", len(files))
print("-> policy PDFs:", len(pdfs))
print("-> setup check:", "PASS" if ok else "FIX THE !! LINES ABOVE")
