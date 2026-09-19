#!/usr/bin/env bash
# تشغيل JARVIS control plane. يقرأ .env عند كل بداية (لذا أعد التشغيل بعد تغيير المفتاح).
set -e
cd "$(dirname "$0")"
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
