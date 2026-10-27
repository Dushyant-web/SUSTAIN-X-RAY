"""Explicit one-time historical seed for either storage backend."""

import json
import os
from .main import ROOT, stable_id, stamped
from .models import Bill
from .store import Store, FirestoreStore

store = (
    Store(os.getenv("LOCAL_DB_PATH", str(ROOT / "data/local.sqlite")))
    if os.getenv("APP_MODE") == "local"
    else FirestoreStore()
)
rows = []
for b in json.loads((ROOT / "data/bills.json").read_text()):
    r = Bill(**b).model_dump(mode="json")
    i = stable_id("bills", r)
    if not store.get("bills", i):
        rows.append(stamped(r, {"uid": "source-seed"}, i))
if rows:
    store.insert_many("bills", rows)
print(f"Imported {len(rows)} source-backed bills. No water readings or savings seeded.")
