"""Static regression checks for ChatViewModel transport/auth/retry stability."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
chat = (root / "JARVIS/Workspace/ChatViewModel.swift").read_text(encoding="utf-8")
api = (root / "JARVIS/Workspace/JarvisAPI.swift").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/ios-build.yml").read_text(encoding="utf-8")

checks = {
    "chat uses centralized authenticated transport": 'try api.request(' in chat,
    "session and workspace headers are centralized": all(h in api for h in ['X-Jarvis-Session', 'X-Jarvis-Workspace']),
    "HTTP is validated before parsing": chat.index('try JarvisAPI.validate(response)') < chat.index('for try await byte in bytes'),
    "MIME is checked": 'response.mimeType == "text/event-stream"' in chat,
    "silent stream termination fails": 'guard terminalReceived else { throw JarvisAPIError.interrupted }' in chat,
    "concurrent sends are guarded": 'guard !isSending, !isLoading else { return }' in chat,
    "retry uses stable request id": '"client_msg_id": requestID' in chat and 'if pendingRequestID != nil { await transmit() }' in chat,
    "retry distinguishes load and send": 'else { await load(conversationId) }' in chat,
    "stability branch participates in CI": 'branches: [ main, chatgpt-write-test ]' in workflow,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
