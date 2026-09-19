"""JARVIS storage — original + preview/thumbnail/proxy + indexes (no quality reduction)."""
from __future__ import annotations
import os, json, hashlib, time, uuid

ROOT = os.environ.get("JARVIS_STORAGE_ROOT", "/opt/data/jarvis-storage")
UPLOADS = os.path.join(ROOT, "uploads")
FILES_DIR = os.path.join(ROOT, "files")
DELIVERIES_DIR = os.path.join(ROOT, "deliveries")
FILES_INDEX = os.path.join(ROOT, "files_index.json")
TASKS_INDEX = os.path.join(ROOT, "tasks_index.json")
DELIVERIES_INDEX = os.path.join(ROOT, "deliveries_index.json")

PART_SIZE = 4 * 1024 * 1024  # 4 MB
CONVERSATIONS_INDEX = os.path.join(ROOT, "conversations_index.json")
MESSAGES_INDEX = os.path.join(ROOT, "messages_index.json")
JOBS_INDEX = os.path.join(ROOT, "jobs_index.json")



def ensure_dirs():
    for d in (UPLOADS, FILES_DIR, DELIVERIES_DIR):
        os.makedirs(d, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def _load_index(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_index(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_files() -> dict:
    return _load_index(FILES_INDEX)


def save_files(data: dict) -> None:
    _save_index(FILES_INDEX, data)


def load_tasks() -> dict:
    return _load_index(TASKS_INDEX)


def save_tasks(data: dict) -> None:
    _save_index(TASKS_INDEX, data)


def load_deliveries() -> dict:
    return _load_index(DELIVERIES_INDEX)


def save_deliveries(data: dict) -> None:
    _save_index(DELIVERIES_INDEX, data)
def load_conversations() -> dict:
    return _load_index(CONVERSATIONS_INDEX)

def save_conversations(data: dict) -> None:
    _save_index(CONVERSATIONS_INDEX, data)

def load_messages() -> dict:
    return _load_index(MESSAGES_INDEX)

def save_messages(data: dict) -> None:
    _save_index(MESSAGES_INDEX, data)
def load_jobs() -> dict:
    return _load_index(JOBS_INDEX)

def save_jobs(data: dict) -> None:
    _save_index(JOBS_INDEX, data)

