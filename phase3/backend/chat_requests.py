"""Durable chat request receipts: retries replay events, never repeat tool execution.

A receipt is scoped to user, workspace, conversation and client request ID. A
process crash leaves an unfinished receipt; it must not be automatically rerun
because a downstream tool may already have completed a side effect.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import time
import storage


def _connect():
    os.makedirs(storage.ROOT, exist_ok=True)
    db = sqlite3.connect(os.path.join(storage.ROOT, "chat_requests.sqlite3"), timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS requests (
        scope TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL,
        events TEXT NOT NULL, updated REAL NOT NULL)""")
    return db


def _scope(ident, conversation_id, request_id):
    return json.dumps([ident["user_id"], ident["workspace_id"], conversation_id, request_id])


def claim(ident, conversation_id, request_id, text, attachments):
    scope = _scope(ident, conversation_id, request_id)
    fingerprint = hashlib.sha256(json.dumps([text, attachments or []], sort_keys=True).encode()).hexdigest()
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT fingerprint, state, events, updated FROM requests WHERE scope=?", (scope,)).fetchone()
        if row:
            if row[0] != fingerprint:
                return scope, "conflict", []
            state = row[1]
            if state == "running" and time.time() - row[3] > 300:
                state = "interrupted"
            return scope, state, json.loads(row[2])
        db.execute("INSERT INTO requests VALUES (?, ?, 'running', '[]', ?)", (scope, fingerprint, time.time()))
    return scope, "new", []


def record(scope, events, state="running"):
    with _connect() as db:
        db.execute("UPDATE requests SET events=?, state=?, updated=? WHERE scope=?",
                   (json.dumps(events, ensure_ascii=False), state, time.time(), scope))
