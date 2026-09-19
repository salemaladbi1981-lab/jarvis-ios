# One-shot Deployment Plan — UPG-2 + Phase A/B/C (للمراجعة — لا تنفيذ)

التاريخ: 2026-09-19. الحالة: **قيد المراجعة — READY TO DEPLOY: NO** (انظر §7).

---

## 1. نقطة البداية (مثبّتة من runtime، لا من اسم branch)

| البند | القيمة (مثبتة) |
|---|---|
| SOURCE SHA | `55b340eaf3f43b976d0a99d4492bd4d6bfb8866e` |
| branch | `feat/master-build-v1` (شجرة نظيفة) |
| live backend | **ليس git checkout** — مسار `/opt/data/workspace/jarvis-native/phase3/backend/` |
| live fingerprint | manifest SHA256 لـ 54 ملفًا → `docs/upgrade/LIVE_FINGERPRINT_20260919.md` + `.json` |
| آخر نشر موثّق | UPG-1 فقط (realtime 6-tool + maps_provider + config) — `DEPLOY_LOG.md` |

### الفرق المحدد (live vs SOURCE، محسوب SHA256 لكل ملف)

| الفئة | العدد | التفسير |
|---|---|---|
| **NEW** (في source فقط) | 30 | وحدات UPG-2 + Phase A/B/C + الاختبارات — تُنشر |
| **CHANGED** (في الطرفين ومختلفة) | 14 | تعديلات UPG-2/Phase على ملفات أساسية — تُنشر **لكنها مصدر الخطر** (§3) |
| IDENTICAL | 30 | لا تُنشر |
| ORPHAN (في live فقط) | 10 | `.env`, `run.sh`, `safe_tools.py`, `live_test_harness.py`, `tests.py`, `tests_barge_in.py`, `tests_m34.py`, `audit.jsonl`, `.gitignore`, `.env.bak` |

**ملفات ستتغير بالنشر = 44** (30 NEW + 14 CHANGED).

الـ 14 CHANGED (الملفات الأساسية المتغيّرة):
`approval.py, audit.py, auth.py, brain_tools.py, config.py, deliveries.py, files_api.py, main.py, orchestrator.py, realtime.py, requirements.txt, tasks.py, tests_maps.py, tools.py`

---

## 2. تعريف Phase A/B/C (مستخرج من المصدر المعتمد — لا تخمين)

المصدر: docstrings ملفات الاختبار + `DEPLOY_LOG.md` + `REQUIREMENTS_MATRIX.md`.

| Phase | الغرض | الملفات | اختبار القبول | الحالة |
|---|---|---|---|---|
| **A — Memory** | recall من ملف + سجل محادثات + miss + خصوصية audit + identity scoping | `memory_bridge.py`, `memory_tools.py`, `audit_memory.py`, `identity.py` | `tests_memory.py`, `tests_memory_isolation.py` (23/23) | NOT deployed |
| **B — Capability Registry** | سجل قدرات مع status model + validation | `capabilities.py` (موجود)، `capabilities_tools.py`, `JARVIS-CAPABILITIES.json` | `tests_capabilities.py` | NOT deployed (capabilities.py موجود قديمًا) |
| **C — Agent Execution Model** | تنفيذ وكيل + enforcement + persistence + privacy | `agent_profiles.py`, `agent_runner.py`, `agent_state.py`, `agent_audit.py`, `agent_tools.py` | `tests_agents.py` (**9/16 FAIL على source**) | NOT deployed |

(الملحق A/B في مستند التنفيذ = مواصفة البناء الأصلية + طلب الاستقرار — **مختلفان** عن Phase A/B/C هذه.)

---

## 3. النتيجة الحرجة: تباعد (divergence) بين source و live

**أثبتُّ من runtime أن الـ source ليس superset للـ live، بل تباعدا في اتجاهين مختلفين:**

| الملف | live (الحالي) | source (git) | الخطر |
|---|---|---|---|
| `orchestrator.py` | **5034B** — `classify()` (sensitive_action/safe_read/reminders/calendar…)، `ROUTES` (core_home/ct_account/ct_director/sys_server)، `_tool_for()`، `handle(text, session_id, audit)` | 2050B — ROUTING عام (home/calendar/media) + `handle(agent_id, action, params)` | **نشر source يرجّع live** (يفقد classify + routing المحدد) |
| `tools.py` | **2430B** — `risk_class` (medium/high) + `bypass_approval` + `contract()/all_contracts()` | 1597B — `risk` (low/med/high) + `approval_rule` + `schema()` | **نشر source يغيّر نموذج الأدوات** (يفقد risk_class/bypass_approval/contracts) |
| `brain_tools.py` | 2213B | 3100B | مختلف (الاتجاه المعاكس) |

**الاستنتاج:** عمل UPG-2/Phase في الـ git بُني على **أساس قديم** من orchestrator/tools، بينما الـ live تطوّر **بموازاة** (classify + risk_class + contracts). النشر «نسخ git → live» سيرجّع ميزات الـ live الحالية.

لذلك **لا يجوز** النشر الأحادي كنسخ مباشر قبل **تسوية التباعد** (reconcile).

---

## 4. خطة النشر (مشروطة بتسوية التباعد أولًا)

### المرحلة 0 — التسوية (blocker الحالي)
1. استيراد ملفات الـ live الحالية (orchestrator.py, tools.py, brain_tools.py, main.py) إلى الـ git كـ baseline.
2. إعادة تطبيق تغييرات UPG-2/Phase **فوق** هذا الأساس (rebase يدوي): workspace_id، approvals، audit chain، kill_switch، tool_guard، memory isolation، agent enforcement.
3. التأكد أن `main.py` الجديد يجمع بين: live orchestrator (classify) + UPG-2 (workspace/approval/audit) + Phase C (agent_runner).
4. إعادة تشغيل مجموعة الاختبارات كاملة — **يجب أن تتحول tests_agents من 9/16 إلى أعلى** (لا انتشار لنسخة فيها FAIL).

### المرحلة 1 — preflight (بعد التسوية)
- تثبيت SOURCE SHA الجديد + live fingerprint الحالي.
- تحقق: backend حي (`/health`)، gateway حي (`8642`)، restricted profile حي (`/p/jarvis-agent/`).

### المرحلة 2 — backups
- نسخة كاملة من `/opt/data/workspace/jarvis-native/phase3/backend/` إلى `deploy-backup-<ts>/` (كل الملفات + `.env`).
- حفظ manifest SHA256 ما قبل النشر.

### المرحلة 3 — config validation
- `config.py` يضم `JARVIS_HERMES_PROFILE` (موجود في source) + توجيه الوكيل.
- `.env` يضم `JARVIS_HERMES_PROFILE=jarvis-agent` (مثبت فعلًا).

### المرحلة 4 — code deployment
- نشر 30 NEW + 14 CHANGED (بعد تسوية §0) إلى live.
- `py_compile` لكل ملف قبل/بعد.

### المرحلة 5 — migrations
- `memory_store.py` ينشئ `/memories/<ws>/index.json` كسولًا — **لا migration يدوي**.

### المرحلة 6 — restart
- backend فقط (kill uvicorn → watchdog). gateway لا يُلمس (منفصل، مقيّد سابقًا).

### المرحلة 7 — verify (§5 مصفوفة القبول).

### المرحلة 8 — rollback (§6).

---

## 5. مصفوفة القبول على live (PASS/FAIL — لا اعتماد على رفض نصي وحده)

| # | الاختبار | الطريقة (runtime/سجلات/أثر، لا نصّي) |
|---|---|---|
| 1 | backend health | `GET /health` → `{"ok":true}` |
| 2 | gateway health | `GET :8642/` (404 متوقع) + `/v1/chat/completions` بلا مفتاح → 401 |
| 3 | restricted profile reachable | `/p/jarvis-agent/v1/toolsets` → 200 |
| 4 | allowed tool succeeds | `web_search` عبر الـ profile → استجابة |
| 5 | terminal blocked | toolsets: `terminal.enabled=false` + سجل عدم وجود أداة |
| 6 | file blocked | `file.enabled=false` |
| 7 | code_execution blocked | `code_execution.enabled=false` |
| 8 | skills blocked | `skills.enabled=false` |
| 9 | delegation blocked | `delegation.enabled=false` |
| 10 | no fallback | toolsets للـ profile = `web/vision/image_gen` فقط (لا skills/terminal) |
| 11 | fail-closed | `/p/evil/v1/chat/completions` → 404/رفض |
| 12 | Agent→Skill/Tool routing | حسب السياسة (المرحلة 0 تحدد) |
| 13 | Phase A | `tests_memory.py` + `tests_memory_isolation.py` على live |
| 14 | Phase B | `tests_capabilities.py` على live |
| 15 | Phase C | `tests_agents.py` على live |
| 16 | regression (restricted profile) | إعادة §4–§10 بعد النشر (أي تراجع = فشل) |
| 17 | regression (integrations) | email/instagram/telegram/youtube تبقى كما هي (30 ملف identical) |

---

## 6. التراجع (single clear rollback)

- **trigger:** أي FAIL في §5 (خاصة 5–11 أو 16–17) → rollback فوري، **لا إصلاح live أثناء النافذة**.
- **الإجراء:** استعادة `deploy-backup-<ts>/` كاملًا فوق live + إعادة تشغيل backend (kill → watchdog) + إعادة تحقق §5 بنود 1–2 و 5–11.
- **الإثبات المسبق:** الـ manifest (54 ملفًا SHA256) محفوظ في `docs/upgrade/LIVE_FINGERPRINT_20260919.*` + النسخ الاحتياطية `.deploy-backup-*` السابقة + `.env.bak-*` موجودة.

---

## 7. أثر الخدمة

- **انقطاع قصير** (ليس zero-downtime): إعادة تشغيل uvicorn للـ backend فقط (jarvis-api.qeyas.app :8000).
- المتأثر: **backend JARVIS فقط**. الـ gateway (8642) و Telegram (المساعد الرئيسي) **غير متأثرين** (عمليات منفصلة).
- لا تقديرات زمنية غير مثبتة؛ مدة الانقطاع = زمن إعادة تشغيل uvicorn + تدفئة الـ import.

---

## 8. نقطة القرار

### READY TO DEPLOY: **NO**

السبب: **تباعد مثبت بين source و live** (§3) — نشر source الحالي سيرجّع live (يفقد classify/risk_class/contracts). يلزم أولًا تسوية التباعد (§4 مرحلة 0) ثم إعادة تشغيل الاختبارات، وعندها أعيد التقييم إلى YES مع الأمر الدقيق.

ما أحتاجه منك: قرار بشأن §4 مرحلة 0 — هل أبدأ التسوية (استيراد live الحالي كأساس + إعادة تطبيق UPG-2/Phase فوقه + تحويل tests_agents إلى أخضر)؟
