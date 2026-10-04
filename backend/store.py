"""SQLite persistence with atomic writes and isolated owner records."""
import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(os.environ.get("ECHO_DB", Path(__file__).parent / "echo.db"))

@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
          display_name TEXT NOT NULL, pin_hash TEXT NOT NULL, failed_attempts INTEGER DEFAULT 0,
          lock_until REAL DEFAULT 0, last_seen TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), expires REAL, unlocked INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reviews (
          id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), created_at TEXT, deleted INTEGER DEFAULT 0, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plans (
          id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decisions (
          user_id TEXT REFERENCES users(id), key TEXT, PRIMARY KEY(user_id,key));
        ''')

def put(table, record, user_id):
    assert table in {"reviews", "plans"}
    with connect() as db:
        if table == "reviews":
            db.execute("INSERT INTO reviews VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET deleted=excluded.deleted,data=excluded.data",
                       (record["id"], user_id, record["created_at"], int(record.get("deleted", False)), json.dumps(record)))
        else:
            db.execute("INSERT INTO plans VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (record["id"], user_id, json.dumps(record)))
    return record

def records(table, user_id, deleted=False):
    assert table in {"reviews", "plans"}
    with connect() as db:
        query = f"SELECT data FROM {table} WHERE user_id=?"
        if table == "reviews" and not deleted:
            query += " AND deleted=0"
        result = [json.loads(r[0]) for r in db.execute(query, (user_id,))]
    from knowledge import RULES
    aliases = RULES.get("legacy_topic_aliases", {})
    for record in result:
        if table == "reviews":
            for topic in record["topics"]:
                topic["topic"] = aliases.get(topic["topic"], topic["topic"])
        elif "key" in record:
            topic, sentiment = record["key"].split(":")
            record["topic"] = aliases.get(topic, topic)
            record["key"] = record["topic"] + ":" + sentiment
    return result
