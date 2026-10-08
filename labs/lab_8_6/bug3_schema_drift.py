"""BUG 3: the vendor shipped v3 of their API. Nothing crashes, but look at the output."""

import json

import pandas as pd

page = json.loads(open("labs/lab_8_6/forms_page_v3.json", encoding="utf-8").read())
df = pd.json_normalize(page["value"], sep="_")
df = df.reindex(columns=["Id", "MemberNumber", "WhatHappened", "ComplaintCategory"])  # "keep the columns we use"
print("-> entries:", len(df))
print("-> entries with a narrative:", int(df["WhatHappened"].notna().sum()))
