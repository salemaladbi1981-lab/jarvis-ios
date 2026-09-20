"""Static regression checks for ChatViewModel transport/auth/retry stability."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
chat = (root / "JARVIS/Workspace/ChatViewModel.swift").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/ios-build.yml").read_text(encoding="utf-8")

checks = {
    "chat request carries session header": 'forHTTPHeaderField: "X-Jarvis-Session"' in chat,
    "chat request carries workspace header": 'forHTTPHeaderField: "X-Jarvis-Workspace"' in chat,
    "empty session fails before transport": 'guard !api.sessionToken.isEmpty else' in chat,
    "chat handshake has explicit timeout": 'req.timeoutInterval = 45' in chat,
    "HTTP status is validated before SSE parsing": 'guard (200..<300).contains(http.statusCode)' in chat,
    "401 has session-specific error": 'case 401:' in chat and 'أعد ربط الجهاز' in chat,
    "403 has authorization-specific error": 'case 403:' in chat,
    "offline error is distinguished": '.notConnectedToInternet' in chat,
    "timeout error is distinguished": '.timedOut' in chat,
    "network loss error is distinguished": '.networkConnectionLost' in chat,
    "silent SSE termination is detected": 'انتهى الاتصال قبل اكتمال الرد' in chat,
    "concurrent/repeated requests are guarded": 'guard !requestInFlight else { return }' in chat,
    "retry reuses text without appending duplicate local user": 'appendLocalUserMessage: false' in chat,
    "retry target distinguishes load and send": 'case load(String)' in chat and 'case send(String)' in chat,
    "stability branch participates in CI": 'branches: [ main, chatgpt-write-test ]' in workflow,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
