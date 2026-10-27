"""Small repository boundary. SQLite is an explicit local fallback, never production storage."""

import json
import os
import sqlite3
from pathlib import Path

COLLECTIONS = [
    "users",
    "buildings",
    "meters",
    "readings",
    "bills",
    "alerts",
    "maintenanceTickets",
    "actionVerifications",
    "sustainabilitySnapshots",
    "settings",
]


class Store:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS records (collection TEXT, id TEXT, body TEXT, PRIMARY KEY(collection,id))"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def all(self, c):
        with self.connect() as db:
            return [
                json.loads(r[0])
                for r in db.execute("SELECT body FROM records WHERE collection=?", (c,))
            ]

    def get(self, c, i):
        with self.connect() as db:
            r = db.execute(
                "SELECT body FROM records WHERE collection=? AND id=?", (c, i)
            ).fetchone()
            return json.loads(r[0]) if r else None

    def put(self, c, i, v):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO records VALUES(?,?,?)", (c, i, json.dumps(v))
            )

    def insert_many(self, c, rows):
        with self.connect() as db:
            for v in rows:
                db.execute(
                    "INSERT INTO records VALUES(?,?,?)", (c, v["id"], json.dumps(v))
                )


class FirestoreStore:
    def __init__(self):
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                options={"projectId": os.environ["FIREBASE_PROJECT_ID"]}
            )
        self.db = firestore.client()

    def all(self, c):
        return [d.to_dict() for d in self.db.collection(c).stream()]

    def get(self, c, i):
        return self.db.collection(c).document(i).get().to_dict()

    def put(self, c, i, v):
        self.db.collection(c).document(i).set(v)

    def insert_many(self, c, rows):
        batch = self.db.batch()
        for v in rows:
            batch.create(self.db.collection(c).document(v["id"]), v)
        batch.commit()
