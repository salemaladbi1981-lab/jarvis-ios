# Restricted Hermes Profile — خطة التنفيذ (الخيار 1)

الهدف: إغلاق `HERMES_NATIVE_TOOL_ENFORCEMENT` بمنع تقني حقيقي أثناء التنفيذ — مسار `jarvis_agent`
يعمل داخل Hermes profile مقيّد بأدوات دنيا، فلا يمكن لأي prompt/agent/mode تجاوزها (الأدوات غير
المصرح بها غير موجودة أصلًا في runtime ذلك الـ profile).

## المرجع الفني (من المصدر v0.21.0)

- `gateway/config.py:980` — `multiplex_profiles: bool = False` (افتراضيًا معطّل).
- `gateway/config.py:983` — `multiplex_profile_allowlist: Optional[List[str]]`.
- `gateway/platforms/api_server.py:36` — مسار `POST /p/<profile>/v1/chat/completions`.
- `toolsets.py:103` — `TOOLSETS` (web/search/vision/terminal/skills/browser/file/code_execution/delegation/memory/…/`safe` سطر 376).
- `_get_platform_tools(config, "api_server", …)` — الأدوات المفعلة للمنصة.

## الخطوات (تتطلب صلاحية root على `/opt/hermes` — خارج نطاق كتابتي الحالية)

1. **إنشاء profile مقيّد** `jarvis-agent` (config/skills/memory معزولة) عبر آلية profiles في Hermes.
2. **تقييد الأدوات**: في config الـ profile، تفعيل toolsets دنيا فقط — `safe` (+ ربما `memory`/`search` للقراءة) — وتعطيل: `terminal`, `skills`, `browser`, `file`, `code_execution`, `delegation`, `cronjob`, `web`, `computer_use`.
3. **تفعيل multiplexing**: `gateway.multiplex_profiles = true` + `multiplex_profile_allowlist = ["default", "jarvis-agent"]` (fail-closed: أي profile غير مُدرج يُرفض).
4. **توجيه agent_runner**: ضبط `JARVIS_HERMES_PROFILE=jarvis-agent` (مدعوم في الكود أدناه) ليجعل الاستدعاء `/p/jarvis-agent/v1/chat/completions`.

## ما أُنجز ضمن الصلاحيات الحالية (كود المصدر)

- `agent_runner.py` أصبح profile-aware: يقرأ `config.JARVIS_HERMES_PROFILE` ويبني URL الـ `/p/<profile>/v1/chat/completions`.
- `config.py`: متغير `JARVIS_HERMES_PROFILE` (افتراضي فارغ = السلوك الحالي بلا تغيير).

## اختبارات الإنفاذ (بعد النشر)

- طلب عبر `/p/jarvis-agent/` مهمة تحتاج `terminal`/`skills`/`file` → **يُرفض/أداة غير متاحة** (منع حقيقي).
- طلب قراءة بسيط عبر الـ profile المقيّد → يعمل.
- الـ profile الافتراضي (`/v1/chat/completions`) → يحتفظ بالأدوات الكاملة.
- محاولة حقن تعليمات داخل المهمة تطلب `terminal` → لا تنفذ (الأداة غير موجودة في الـ runtime).

## الحالة

- `UPG-2` يبقى مفتوحًا حتى: إنشاء الـ profile + تمكين multiplexing + تشغيل اختبارات الإنفاذ.
- لا نعتمد prompt-level بديلًا عن المنع أثناء التنفيذ.
