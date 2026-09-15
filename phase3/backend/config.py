"""Secrets live ONLY in backend environment variables — never in clients/git."""
import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Realtime provider preference
REALTIME_PROVIDER = os.environ.get("JARVIS_REALTIME_PROVIDER", "openai")  # openai | openrouter
REALTIME_MODEL = os.environ.get("JARVIS_REALTIME_MODEL", "gpt-4o-realtime-preview")
SESSION_TTL_SECONDS = int(os.environ.get("JARVIS_SESSION_TTL", "3600"))
