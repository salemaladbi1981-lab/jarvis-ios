# UPG-3 — JARVIS Unified Conversation & Execution (التعريف المعتمد الجديد)

التاريخ: 2026-09-19. الحالة: DISCOVERY + PLAN فقط — لا بناء، لا تغيير على live.
نقطة الرجوع: `KNOWN_GOOD_BASELINE — UPG-2-LIVE` (`0d6eb83`, tag `UPG-2-LIVE`).

**المبدأ الحاكم:** Telegram والتطبيق واجهتان لنفس JARVIS — هوية واحدة، محادثة واحدة، سياق واحد، خط تنفيذ واحد. لا نظامان منفصلان.

---

## 1. UPG-3 CURRENT STATE (مثبت من الكود)
| المكوّن | الحالة |
|---|---|
| هوية (identity.py) user_id/workspace/session/conversation/memory_namespace | EXISTS (لكن لكل طلب، غير موحّدة عبر المصدرين) |
| session (auth.py) يحمل user_id + workspace_id | EXISTS (لكن **بلا conversation_id**) |
| Telegram | PARTIAL — Telethon **client** (قراءة/إرسال لأدوات الوكيل)، **لا bot نشط** يستقبل ويرسل، **لا handoff** |
| Task model (8 حالات) | EXISTS (لكن بلا worker يدفعها) |
| Chat (jarvis_brain → Hermes) | PARTIAL — تفويض يوجد، **بلا streaming**، **بلا citations** |
| Search | PARTIAL — بحث ويب داخل Hermes، **لا citations مُرجعة** |
| Inbox/Tasks/Deliveries | PARTIAL — Inbox+Deliveries UI موجودان، **Tasks UI مفقود**، **لا deep links** |
| Worker/Pipeline | **MISSING** |
| Resume/Dedup/Notifications | **MISSING** |

## 2. UNIFIED CONVERSATION STATE
| المعرف | الحالة |
|---|---|
| user_id | EXISTS (salem-aladbi، server-side من session) |
| conversation_id | **PARTIAL** — يولَّد لكل طلب تطبيق (identity.new_conversation_id)، لا يُربط بـ Telegram chat، لا يُحفظ في session |
| task_id | EXISTS (لكن بلا worker) |
| session_id | EXISTS (لكن يحمل user+workspace فقط، لا conversation) |
| attachment_ids | EXISTS (files_api يربط conversation_id) |
| memory/context | PARTIAL — memory_namespace مربوط بـ conversation_id، لكن **لا conversation موحّد** |
| agent execution state | PARTIAL — agent_state (verified) موجود، لكن **غير مربوط بالمحادثة/المهمة** |

## 3. TELEGRAM ↔ APP HANDOFF STATE
| المتطلب | الحالة |
|---|---|
| طلب بسيط يُجاب inline | **MISSING** — لا bot نشط يرد؛ Telegram مجرد أدوات قراءة/إرسال |
| طلب كبير → Task في التطبيق | **MISSING** |
| نفس conversation_id ينتقل | **MISSING** (لا conversation مشترك) |
| زر/رابط Open in JARVIS | **MISSING** |
| فتح الرابط → نفس conversation/task | **MISSING** (لا deep links) |
| لا محادثة جديدة عند handoff | **MISSING** |

## 4. CHAT / SEARCH STATE
| المتطلب | الحالة |
|---|---|
| streaming response | **MISSING** (jarvis_brain blocking urlopen) |
| conversation history | PARTIAL (عبر Hermes session headers، لا history محلي موحّد) |
| web search | EXISTS (داخل Hermes profile) |
| citations/sources | **MISSING** (answer نص فقط) |
| file attachments في المحادثة | PARTIAL (upload موجود، لا يظهر في chat) |
| tool calls | EXISTS (realtime function calling) |
| agent execution | EXISTS (agent_runner) لكن غير مربوط بالمحادثة |
| task handoff من المحادثة | **MISSING** |
| delivery references | **MISSING** |
| error/retry state | **MISSING** |

## 5. GAP MATRIX (الملخص)
**MISSING (القلب):** Unified conversation runtime · Telegram bot نشط + handoff + deep link · task classification (INLINE vs BACKGROUND) · worker/pipeline · streaming + citations · Tasks UI + deep links · resume/dedup/notifications · media derivatives.

**PARTIAL:** identity (غير موحّد)، session (بلا conversation_id)، chat (بلا streaming/citations)، memory (غير مربوط).

**EXISTS (أساس يُبنى عليه):** identity fields، task/delivery/file models، storage (atomic)، agent_runner، agent_runtime، workspace/approval/audit/kill_switch، Restricted Profile.

## 6. DATA MODEL CHANGES
1. **conversation record** (جديد): `conversation_id → user_id, workspace_id, source (telegram|app), title, created_at, last_activity, task_ids[], attachment_ids[]`.
2. **session** يضيف `conversation_id` (auth.py).
3. **task** يضيف `source` + `conversation_id` (موجود) + `classification` (inline|background).
4. **message record** (جديد): `message_id → conversation_id, role, content, citations[], tool_calls[], delivery_refs[], ts`.
5. **attachment** يرتبط بـ conversation_id (موجود).
6. **agent execution state** يرتبط بـ conversation_id (بدل agent-only).

## 7. API CHANGES
- جديد: `POST /conversations`, `GET /conversations/{id}`, `GET /conversations/{id}/messages`.
- جديد: `POST /chat` (streaming + citations) — SSE.
- `POST /tasks` يضيف `conversation_id` + `source` + يرجع `deep_link`.
- جديد: `POST /classify` (INLINE vs BACKGROUND) — قائم على خصائص المهمة لا كلمات ثابتة.
- جديد: `POST /tg/webhook` (استقبال رسائل Telegram النشط) + `POST /tg/handoff`.
- جديد: `GET /tasks/{id}/events` (progress/status push/poll).
- جديد: `POST /notifications` (app + telegram).
- deep links: `jarvis://conversation/{id}`, `jarvis://task/{id}`, `jarvis://delivery/{id}`.

## 8. IMPLEMENTATION PHASES (مستخرجة من الكود)
- **P1 — Unified Conversation + IDs**: conversation record + session يحمل conversation_id + message record + memory/context مربوط.
- **P2 — Telegram/App Handoff + Classification**: bot نشط (webhook) + classifier (مرفقات كبيرة/خطوات متعددة/rendering/تنفيذ طويل/مخرجات ملفات/retries → BACKGROUND؛ بخلافها INLINE) + Open in JARVIS deep link.
- **P3 — Worker + Task Pipeline**: conversation → task → queue/worker → agent → state → delivery → notification → نفس conversation.
- **P4 — Chat Streaming/Search/Citations/Tools**: `POST /chat` SSE + citations مخزنة مع الرسالة + tool calls + delivery refs.
- **P5 — Tasks/Inbox/Deliveries UI + Deep Links**: TasksView + فتح من المحادثة + deep links بين الشاشات + progress حقيقي.
- **P6 — Resume/Dedup/Notifications**: app killed/backend restart/network interruption/webhook مكرر/upload مكرر/worker restart → لا فقدان ولا تنفيذ مرتين + إشعار (app + telegram) بديبلينك.
- **P7 — Media Derivatives + Cinematic UX**: preview/thumbnail/proxy/transcript (بعد تثبيت pipeline).
- **P8 — End-to-End Acceptance**.

## 9. TEST MATRIX (المضاف الإلزامي)
1. Telegram simple request stays inline
2. Telegram heavy request creates task
3. same conversation_id survives handoff
4. Open in JARVIS opens same task/conversation
5. app continues Telegram conversation
6. app → task → delivery
7. web search returns citations
8. streaming works
9. attachment context preserved
10. duplicate Telegram webhook does not duplicate task
11. worker restart resumes
12. backend restart preserves state
13. notification links to correct task
14. Restricted Profile remains enforced
+ regression UPG-2 (workspace 19/19، agents 16/16، tool_guard 9/9).

## 10. FILES EXPECTED TO CHANGE
- **جديد (backend)**: `conversation.py`, `classifier.py`, `worker.py`, `chat.py` (SSE+citations), `notifications.py`, `tg_bot.py` (webhook), `derivatives.py` + اختباراتها.
- **معدّل (backend)**: `main.py` (endpoints)، `auth.py` (conversation_id)، `identity.py`، `tasks.py`، `memory_bridge.py` (conversation scope)، `brain_tools.py` (citations).
- **جديد (Swift)**: `TasksView.swift`, `ChatView.swift`, `DeepLinkHandler.swift`.
- **معدّل (Swift)**: `ContentView`/`BottomNavBar` (Tasks/Chat tabs)، `JarvisAPI` (chat SSE + deep links)، `UploadManager`.

## 11. RISKS
- Telegram bot نشط = مصدر جديد للدخول (auth + rate limit + webhook security).
- concurrency على indexes مشتركة (storage atomic موجود، لكن worker يحتاج قفل).
- agent cost/time للـ worker (غير متزامن + timeout).
- streaming عبر SSE يحتاج بنية مختلفة عن blocking الحالي.
- regression UPG-2/Restricted Profile = rollback فوري (نقطة `UPG-2-LIVE`).

## 12. ROLLBACK STRATEGY
- نقطة الرجوع: `UPG-2-LIVE` (`0d6eb83`) + `deploy-backup-20260919-121929/` + manifest `live_fingerprint_POSTDEPLOY_20260919.json`.
- كل Phase يُنشر كمرحلة مستقلة باختباراتها؛ أي FAIL = استعادة + إعادة تشغيل (لا ترقيع live).
- Restricted Profile / multiplexing / .env لا تُمس في UPG-3.

---

## UPG-3 READY TO BUILD: **YES** (بعد اعتماد هذه النسخة)
التعريف الجديد يغيّر الترتيب: **P1 = الهوية والمحادثة الموحدة** (وليس worker)، ثم handoff/classification، ثم pipeline. الأساس (identity/task/delivery/agent) موجود ويُبنى عليه.
