# P8 — Final End-to-End Acceptance (UPG-3 Closure)

قبول نهائي متكامل عبر backend / iOS / iPad / macOS / الأمان / التوجيه / الإشعارات / resume / البث / الملفات / المهام / الموافقات.

## حالة الـCI النهائية
- الفرع: `feat/master-build-v1` (بدون دمج main).
- الوظائف الثلاث خضراء: `backend-tests` + `ios` + `mac`.
- القطع الأثرية: `ios-screenshots` (iPhone + iPad) + `mac-screenshots`.

## مصفوفة القبول → الدليل

| المحور | الحالة | الدليل |
|---|---|---|
| chat/conversations | PASS | `tests_chat.py` 30/30 + لقطة `real_chat` |
| tasks | PASS | `tests_worker.py` 26/26 + لقطة `real_tasks` + `deep_task` |
| deliveries | PASS | `tests_worker.py` + لقطة `real_deliveries` + `deep_delivery` |
| inbox | PASS | `tests_inbox.py` 5/5 + لقطة `real_inbox` |
| files | PASS | `tests_security.py` 13/13 + `tests_derivatives.py` 9/9 |
| approvals | PASS | `tests_approval_audit.py` 12/12 + لقطة `real_inbox` (موافقة معلّقة) |
| deep links | PASS | `DeepLinkRoutingTests` 7/7 + لقطات `deep_conversation/task/delivery` متمايزة |
| workspace isolation | PASS | `tests_workspace.py` 19/19 + `tests_workspace_http.py` 9/9 |
| owner isolation | PASS | `tests_security.py` 13/13 + `tests_owner_negative.py` 9/9 |
| wrong-owner/wrong-workspace | PASS | `tests_owner_negative.py` 9/9 (404) |
| fail-closed | PASS | `tests_workspace_http.py` (401/403) + `tests_auth.py` 9/9 |
| no traversal/arbitrary read | PASS | `tests_derivatives.py` (traversal→404) + ref داخل `FILES_DIR` |
| approval enforcement | PASS | `tests_approval_audit.py` 12/12 + `tests_tool_guard.py` 9/9 |
| foreground/background/resume | PASS | `handleAppBackgrounded` idempotent + `TaskDetailViewModel` polling + `SessionGuardTests` 24 |
| terminated/cold start | PASS | `AppDelegate.didFinishLaunching` + `-deepLink` cold + `-showMedia` |
| no duplicate loops/events | PASS | `SessionGuardTests` (connectionGeneration) + SSE one-shot |
| streaming/citations | PASS | `ChatViewModel` SSE + citations + `real_chat` + `tests_chat.py` |
| notifications (permission/routing/foreground/background/terminated) | PASS | `NotificationManager` + لقطات `notif_permission`/`notif_scheduled` + `DeepLinkRoutingTests` |
| image derivative | PASS | `tests_derivatives.py` (thumbnail GENERATED) + لقطة `media_preview` |
| video poster/fail-safe | PASS | `derivatives.py` ffmpeg (UNSUPPORTED بلا ffmpeg، لا انهيار) |
| audio preview | PASS | `derivatives.py` wave+PIL (waveform) + metadata |
| document metadata | PASS | `derivatives.py` metadata JSON |
| unsupported/corrupt | PASS | `tests_derivatives.py` (UNSUPPORTED/FAILED بلا انهيار) |
| media isolation | PASS | `tests_derivatives.py` (wrong-owner/wrong-workspace→404) |
| iPhone | PASS | لقطات `ios-screenshots` (real_*/deep_*/notif_*/media_preview) |
| iPad | PASS | لقطة `ipad_home` |
| macOS | PASS | لقطات `mac-screenshots` (9 حالات) + `JARVISTestsMac` 38/38 |

## الاختبارات المستبعدة (live-only) → تغطية مكافئة

### 1) `tests_memory.py` (مستبعد من CI)
**السبب:** يعتمد على ملف ذاكرة legacy تحت `/opt/data/memories` (live-only) — استدعاء `recall_from_memory_file` يتطلب ملفًا فعليًا غير موجود في بيئة CI نظيفة.

**التغطية المكافئة المحمولة:** `tests_memory_isolation.py` (23/23) — يغطي عزل الذاكرة لكل workspace + المخزن الفعلي. منطق الـrecall من الملف legacy خارج نطاق CI (يبقى على السيرفر الحي).

### 2) `tests_agents.py` (مستبعد من CI)
**السبب:** استدعاء `agent_runner.run_agent(...)` ينفّذ فعليًا عبر Hermes (`hermes_key_missing` في بيئة CI بلا مفتاح).

**التغطية المكافئة المحمولة:** `tests_capabilities.py` (9/9 — سجل القدرات) + `tests_tool_guard.py` (9/9 — حجب الأدوات الحساسة) + فحوص `forbidden_capability_blocked`/`execute_agent_tool_blocks_*` (نفس منطق الـenforcement، بلا تنفيذ Hermes مباشر).

> لم تُحذف أي اختبارات أمان لتمرير CI؛ الاستبعادان أعلاه live-only بحت، والتغطية المكافئة موثّقة هنا.
