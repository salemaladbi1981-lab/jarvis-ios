# Hermes Native Tool Enforcement — فحص المصدر الفعلي

التاريخ: 2026-09-19. المصدر المفحوص: `/opt/hermes/gateway/platforms/api_server.py` (الـ runtime الفعلي على المنفذ 8642 الذي يستدعيه `agent_runner` عبر `JARVIS_HERMES_API_URL`).

## النتيجة القاطعة

**Hermes `/v1/chat/completions` لا يدعم per-request tool allowlist.** الفجوة حقيقية ومثبتة من المصدر، وليست افتراضًا.

## الدليل (سطر → ماذا يثبت)

| السطر | الدليل |
|---|---|
| `2247` | المسار `POST /v1/chat/completions` → `_handle_chat_completions` |
| `7247-7276` | توقيع `_run_agent(...)` — **لا يوجد معامل `tools`/`tool_choice`/`allowed_tools`/`toolset`**. يقبل فقط: user_message, history, ephemeral_system_prompt, session_id, model/provider/route overrides. |
| `5310-5311` | `"tools", "tool_choice"` تظهر **فقط** في `_make_request_fingerprint` (مفتاح idempotency للـ dedup) — **لا تُستخرج ولا تُنفَّذ** في handler. |
| (لا يوجد `body.get("tools")`) | الـ handler لا يقرأ حقل `tools` من الطلب أصلًا. |
| `4098-4138` | `toolsets` (`/v1/toolsets`) = تصنيف **platform-level** ثابت في config، وليس per-request. |

## ما هو متاح فعلًا (بدل allowlist)

1. **`ephemeral_system_prompt`** — تعليمة نظام تُطبَّق فوق الـ core، وليس تقييد أدوات. هذا ما يستخدمه `agent_runner` حاليًا (`[Allowed tools]`). **Prompt-level لا enforcement تقني.**
2. **`toolsets`** — مجموعات أدوات على مستوى المنصة (ثابتة في config)، لا تُختار لكل طلب.
3. **Per-profile multiplexing** (`/p/<profile>/v1/chat/completions`) — يسمح بملف شخصي منفصل بأدوات معزولة، لكن:
   - الـ gateway الحالي **single-profile** (السطر 70-88: أي `/p/<other>/` يُرفض fail-closed).
   - تفعيله يتطلب: تمكين multiplexing + `multiplex_profile_allowlist` + إنشاء profile مقيّد = **تغيير نشر على مستوى الـ gateway**، ليس تعديل مصدر JARVIS.

## الحالة الصادقة

- `HERMES_NATIVE_TOOL_ENFORCEMENT` = **NOT_SUPPORTED** (مثبت من المصدر).
- الإنفاذ الحالي = `request-level` (بوابة `enforce()` في agent_runner) + `prompt-level` (ephemeral_system_prompt) + `tool_guard` (عند حدود تنفيذ أدوات JARVIS الحساسة).

## خيارات الإغلاق (للقرار، لا للتنفيذ الآن)

1. **Restricted Hermes profile** (يفرض عزلًا حقيقيًا): إنشاء profile باسم `jarvis-agent` بأدوات دنيا (بلا terminal/email/web غير مصرح)، وتمكين multiplexing + allowlist، ثم يوجّه `agent_runner` إلى `/p/jarvis-agent/v1/chat/completions`. — **تغيير نشر** على الـ gateway (root-owned)، يحتاج موافقة سالم.
2. **تعطيل الأفعال الحساسة للمسار** (كما في tool_guard): مسار `jarvis_agent` لا يملك email_send/telegram_send أصلًا، والحساس معطّل تقنيًا بلا موافقة.
3. **قبول prompt-level + request-level** مع الإعلان الصادق (الوضع الحالي).

## القرار المطلوب من سالم
لا يمكن "إغلاق" الفجوة من مصدر JARVIS وحده — هي حدود الـ runtime. الخيار 1 (restricted profile) هو الإغلاق التقني الحقيقي، ويحتاج تعديل نشر الـ gateway + موافقته.
