"""Lab 2.2 - your first API calls with requests."""

import requests

BASE = "http://127.0.0.1:8000"

r = requests.get(f"{BASE}/api/branches", timeout=10)
print("status:", r.status_code, "| content type:", r.headers["content-type"])
data = r.json()
print("-> branches:", data["count"])

url = f"{BASE}/odata/Forms(12)/Entries"
r = requests.get(url, timeout=10) # no token
print("-> status without token:", r.status_code)

r = requests.get(
    url, params={"$top": 1, "$count": "true"}, headers={"Authorization": "Bearer kvcu-forms-demo-token"}, timeout=10
)
print("-> status with token:", r.status_code)
body = r.json()
print("-> total entries (@odata.count):", body["@odata.count"])
print("-> first entry id:", body["value"][0]["Id"])