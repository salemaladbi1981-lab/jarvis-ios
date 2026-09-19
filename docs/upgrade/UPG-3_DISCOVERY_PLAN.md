# UPG-3 — Discovery + Plan (دورة الطلب والمخرجات كاملة)

التاريخ: 2026-09-19. الحالة: **DISCOVERY + PLAN فقط — لا تغيير على live.**
نقطة الرجوع: `KNOWN_GOOD_BASELINE — UPG-2-LIVE` (SHA `0d6eb83`, tag `UPG-2-LIVE`).

---

## 1. UPG-3 CURRENT STATE (مثبت من source + live، لا افتراض)

| المكوّن | الحالة | الدليل |
|---|---|---|
| User Input / Attachment | **EXISTS** | `WorkspaceComposerView` + `AttachmentMenu` + `DocumentScanner` + `CameraCaptureView` |
| API endpoints | **EXISTS** | `/files/upload/{init,part,status,complete}` + `/tasks` + `/deliveries` (+download) |
| Upload (chunked/resumable) | **EXISTS** | `files_api.py` (init/part/status/complete + missing_parts + checksum) + `UploadManager.swift` (resume + progress + state persist) |
| Queue / Worker | **MISSING** | لا worker/queue؛ `create_task` يخزّن `status="uploaded"` فقط ولا شيء يدفع الحالة |
| Agent execution | **PARTIAL** | `agent_runner.py` (Phase C) موجود ويعمل، لكن **غير موصول** بخط المهمة |
| Task state machine | **PARTIAL** | `tasks.py` (8 حالات + `set_status`) موجود، لكن `set_status` **لا يُستدعى أصلًا** (grep=0 خارج الاختبارات) |
| Result generation | **PARTIAL** | `deliveries.create_delivery` موجود، لكن لا worker يولّد المخرج |
| Delivery model | **EXISTS** | `deliveries.py` + download endpoint + `DeliveriesView` (فتح/تنزيل) |
| UI | **PARTIAL** | Inbox + Deliveries موجودان؛ **لا TasksView** (حالة المهمة غير ظاهرة) |

## 2. UPG-3 GAP MATRIX (لكل جزء)

| البند | الحالة | ملاحظة |
|---|---|---|
| نصوص + مرفقات | EXISTS | composer + attachment |
| صور + مستندات | **PARTIAL** | الرفع موجود، لكن **المشتقات** (preview/thumbnail) = `NOT_GENERATED` placeholder |
| ملفات/فيديو كبيرة | **PARTIAL** | chunked يدعم الحجم، لكن **proxy/transcript** = placeholder |
| upload progress | EXISTS | `UploadManager.progress` |
| resumable uploads | EXISTS | `upload_status` → `missing_parts` |
| retry/استئناف (مهمة) | **PARTIAL** | الرفع قابل للاستئناف، **المهمة ليست** |
| منع duplicate jobs | **MISSING** | لا idempotency على إنشاء المهمة |
| persistence بعد restart | **PARTIAL** | البيانات persist (JSON indexes)، لكن **المعالجة لا تستأنف** |
| Inbox | EXISTS | `InboxView` + `list_files` |
| Tasks | **PARTIAL** | backend فقط؛ UI مفقود |
| Deliveries | EXISTS | model + UI + download |
| فتح/تنزيل المخرج | EXISTS | `DeliveriesView.open` + `/download` |
| حالة المهمة في الواجهة | **MISSING** | لا Tasks view ولا polling |
| الأخطاء والاسترداد | **PARTIAL** | upload resumeFailure؛ أخطاء المهمة غير ظاهرة |
| عرض سينمائي فعلي | **MISSING** | المشتقات placeholders؛ لا preview/thumbnail/transcript حقيقي |

**الخلاصة:** كل قطعة منفردة موجودة تقريبًا، لكن **الحلقة المفقودة هي الـ Worker** الذي يربط: upload → task → agent → delivery، ويولّد المشتقات، ويمنع التكرار، ويستأنف بعد الانقطاع.

## 3. DEPENDENCIES
- **موجود وجاهز**: `tasks.py`, `deliveries.py`, `files_api.py`, `storage.py`, `agent_runner.py`, `agent_runtime.py`, `kill_switch.py`, `workspace.py`.
- **جديد مطلوب**: worker (thread/queue) — stdlib (`threading`/`queue` أو `asyncio`) بلا تبعيات خارجية.
- **معالجة وسائط**: `ffmpeg` (proxy/transcript) + `Pillow` (thumbnail) — إن لم تتوفر، تُبنى المشتقات كـ **خطوة لاحقة** ولا توقف الوظيفة الأساسية.
- **Swift**: `UploadManager`, `JarvisAPI`, `InboxView`, `DeliveriesView` (مرجع) — يحتاج `TasksView` جديد.

## 4. IMPLEMENTATION PHASES

**P1 — Worker/Pipeline (القلب المفقود)**
- worker خلفي يقرأ مهمة `uploaded` → ينفّذ `queued→ingesting→analyzing→processing→generating→rendering→ready/failed`.
- يربط `agent_runner.run_agent(selected_agent, prompt+attachments)` → يكتب `deliveries.create_delivery` → `tasks.add_output`.
- idempotency (dedupe بصمة prompt+attachments) + kill_switch يحترم.
- استئناف بعد restart: إعادة المهام العالقة في `processing` إلى `queued`.

**P2 — Derivatives (العرض السينمائي)**
- thumbnail/preview للصور، proxy/transcript للفيديو (ffmpeg)، scene_index.
- يعمل كـ **خطوة اختيارية** لا تكسر الوظيفة إن غابت.

**P3 — Tasks UI**
- `TasksView.swift` (حالة + progress + outputs) + polling خفيف.
- ربط "فتح/تنزيل" المخرج من داخل المهمة.

**P4 — مرونة (retry/resume/dup)**
- retry بتراجع أسي + checkpoint للمهمة + منع duplicate على مستوى API.

**P5 — قبول + عرض سينمائي**
- دورة كاملة حقيقية (نص + صورة → مهمة → معالجة → مخرج) على الجهاز.

## 5. TEST MATRIX
| # | الاختبار | المعيار |
|---|---|---|
| 1 | upload chunked/resumable | part + resume + checksum |
| 2 | create_task → worker يدفع الحالة | status ينتقل `uploaded→…→ready` |
| 3 | agent execution داخل المهمة | delivery يُنشأ بنتيجة حقيقية |
| 4 | duplicate prevention | نفس البصمة → مهمة واحدة فقط |
| 5 | persistence + resume | إعادة تشغيل → المهمة تستأنف لا تفقد |
| 6 | large file/video | رفع 100MB+ + proxy |
| 7 | error recovery | خطأ agent → `failed` + خطأ ظاهر |
| 8 | Inbox/Tasks/Deliveries UI | عرض + فتح/تنزيل |
| 9 | kill_switch يوقف worker | POST /tasks → 503 |
| 10 | workspace isolation مستمر | لا cross-workspace في المهام |
| 11 | Restricted Profile مستمر | terminal/file/skills blocked |
| 12 | regression UPG-2 | tests_agents 16/16 + workspace 19/19 |

## 6. FILES EXPECTED TO CHANGE
- **جديد (backend)**: `worker.py`, `derivatives.py` (+ `tests_worker.py`, `tests_derivatives.py`).
- **معدّل (backend)**: `main.py` (trigger worker), `tasks.py` (dedupe/resume), `files_api.py` (derivatives حقيقية), `config.py` (worker flags).
- **جديد (Swift)**: `JARVIS/Workspace/TasksView.swift`.
- **معدّل (Swift)**: `ContentView`/`BottomNavBar` (تبويب Tasks), `WorkspaceComposerView` (عرض حالة المهمة).

## 7. RISKS
- **worker concurrency**: ملفات indexes مشتركة → تحتاج قفل/atomic write (storage.py يستخدم `os.replace` فعلًا).
- **معالجة فيديو ثقيلة**: ffmpeg قد لا يكون مثبتًا → P2 يبقى خطوة لاحقة.
- **agent cost/time**: مهمة واحدة قد تستهلك وقتًا/تكلفة → worker يعمل غير متزامن + timeout.
- **regression**: أي كسر لـ UPG-2/Restricted Profile = rollback (نقطة الرجوع `UPG-2-LIVE`).

## 8. ROLLBACK STRATEGY
- **نقطة الرجوع**: `UPG-2-LIVE` (`0d6eb83`) + backup `deploy-backup-20260919-121929/` + manifest `live_fingerprint_POSTDEPLOY_20260919.json`.
- أي FAIL في مصفوفة الاختبار → استعادة الملفات السابقة + إعادة تشغيل backend (لا ترقيع live أثناء فشل غير مفهوم).
- UPG-3 يُنشر **كمرحلة مستقلة** بعد UPG-2 (لا يمس Restricted Profile).

---

## UPG-3 READY TO BUILD: **YES** (بعد مراجعة الخطة)
القلب المفقود معروف بدقة (worker + derivatives + Tasks UI)، والقطع الأساسية كلها موجودة، ولا تبعيات خارجية معطِّلة للـ P1.
