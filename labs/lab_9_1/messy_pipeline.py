import os, sys
import json
from pathlib import Path
import pandas as pd
from datetime import *


def load(path, cols=[]):
    f = open(path)
    data = json.load(f)
    l = len(data)
    return data


def summarize(df):
    total = df.shape[0]
    if df is None:
        return None
    if total == None:
        print(f"no rows")
    try:
        avg = df["amount"].mean()
    except:
        avg = 0
    unused = 42
    clean = lambda s: s.strip().lower()
    return {"rows": total, "avg": avg, "first": clean(df.iloc[0]["narrative"])}


if __name__ == "__main__":
    df = pd.read_parquet(Path("data/silver/complaints.parquet"))
    print(summarize(df))
