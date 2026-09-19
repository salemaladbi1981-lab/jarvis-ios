# JARVIS — Requirements Matrix (UPG execution)

حالات الثقة: `SOURCE_IMPLEMENTED` / `BUILD_PASSED` / `BACKEND_TEST_PASSED` / `LIVE_DEPLOYED` / `DEVICE_TEST_PASSED` / `ACCEPTED` / `NOT_STARTED` / `PENDING`.
لا تُستنتج حالة من أخرى. آخر تحديث: 2026-09-19. رأس الفرع: `617b110` + إصلاحات UPG-1.

---

## STABILITY — الصوت والمقاطعة
- source_reference: ملحق B §2
- current_evidence: commit `4aa76e5` — realtime.py (تنفيذ أدوات بمهمة منفصلة + turn_generation + سجلّات منظمة)، RealtimeVoiceSession (truncate + تتبّع item)
- gap: اختبار جهاز (10 مقاطعات / 20 دقيقة / Bluetooth) غير منفّذ
- implementation_files: `phase3/backend/realtime.py`, `JARVIS/Voice/RealtimeVoiceSession.swift`, `VoiceAudioEngine.swift`, `SessionEventParser.swift`
- dependency: OpenAI Realtime (voice `verse`)
- backend_test: `tests_voice_stability.py` 16/16 PASS
- live_deploy_fingerprint: NOT_DEPLOYED
- app_build: BUILD_PENDING
- device_test: DEVICE_PENDING
- acceptance: PENDING
- last_tested_at: 2026-09-19 (source-level)
- blocker: لا Mac/Xcode/iPhone على هذا السيرفر

## STABILITY — الموقع والملاحة
- source_reference: ملحق B §1
- current_evidence: commit `395930a` — Core Location (When In Use) + HeaderView مدينة حقيقية + dir_action=navigate + Info.plist
- gap: اختبار جهاز (granted/denied/reduced/عودة من الخرائط) غير منفّذ
- implementation_files: `Providers/LocationManager.swift`, `JARVIS/Home/HeaderView.swift`, `JARVIS/Info.plist`, `phase3/backend/maps_provider.py`, `JARVIS/App/JarvisMapsIntent.swift`
- dependency: CoreLocation, CLGeocoder
- backend_test: `tests_maps.py` 17/17 PASS
- live_deploy_fingerprint: NOT_DEPLOYED
- app_build: BUILD_PENDING
- device_test: DEVICE_PENDING
- acceptance: PENDING
- last_tested_at: 2026-09-19 (source-level)
- blocker: لا Mac/Xcode/iPhone هنا

## STABILITY — اللغة واللكنة
- source_reference: ملحق B §3
- current_evidence: commit `ae6f30f` — إزالة «وليس المصرية أبداً»، الخليجية افتراضي فقط، أولوية الطلب الصريح
- gap: استماع فعلي (خليجية/بريطانية/فرنسية/مصرية) غير منفّذ
- implementation_files: `phase3/backend/config.py`
- dependency: لا (override `JARVIS_REALTIME_INSTRUCTIONS` غير مضبوط — مؤكّد)
- backend_test: `tests_config_language.py` 6/6 PASS
- live_deploy_fingerprint: NOT_DEPLOYED
- app_build: n/a (backend only)
- device_test: DEVICE_PENDING
- acceptance: PENDING
- last_tested_at: 2026-09-19 (source-level)
- blocker: تقييم جودة النطق يحتاج استماع سالم

## MEDIA — الاستقبال/الرفع/المخرجات (من طلبات سالم السابقة)
- source_reference: ملحق B §4 + طلبات المرفقات + القسم 6 من V2.0
- current_evidence: Phase D CODE COMPLETE + إصلاح رفع part `617b110` محفوظ
- gap: دورة كاملة (صورة→رفع→Task→Delivery) غير مثبتة على الجهاز
- implementation_files: `JARVIS/Upload/`, `JARVIS/Workspace/`, `phase3/backend/{files_api,storage,tasks,deliveries,auth}.py`
- backend_test: `tests_upload_auth` 9/9، `tests_phaseD` 13/13، `tests_enrollment` 6/6، `tests_security` 12/12
- live_deploy_fingerprint: PARTIAL (backend منشور سابقًا، لم يُعَد نشره بهذا الدفعة)
- app_build: BUILD_PENDING
- device_test: DEVICE_PENDING
- acceptance: PENDING

---

## MODULES M1–M10 (الوحدات العشر — لاحقة، ليست ضمن UPG-1)

| ID | الوحدة | الحالة | blocker |
| --- | --- | --- | --- |
| M1 | Autonomous inbox + briefings | NOT_STARTED | تفويض بريد/جدولة + سياسة تشغيل |
| M2 | Auto-planning calendar | NOT_STARTED | تفويض تقويم |
| M3 | Concierge + end-to-end | NOT_STARTED | تكامل حجوزات مصرّح |
| M4 | Domain agents (6) | NOT_STARTED | mapping إلى profiles + عزل |
| M5 | Meetings + Desktop folder | NOT_STARTED | رفيق الماك |
| M6 | Trigger engine | NOT_STARTED | webhook/جدولة |
| M7 | Unified memory + analytics | NOT_STARTED | عزل مساحة + منهج تقدير |
| M8 | Instant retrieval | NOT_STARTED | فهارس المصادر |
| M9 | Private vaults | NOT_STARTED | معالجة محلية على الماك |
| M10 | Differentiators («يا جارفس»/Share/vault) | NOT_STARTED | نطاق لاحق + iOS ثم Android |

---

## اختبارات منع تكرار الأخطاء (Q01–Q28)
رصد أولي: Q01 (clean build) و Q02–Q06 (الصوت/الموقع/اللغة) و Q07 (لا مدينة ثابتة) و Q08–Q11 (رفع/مهمة/مخرج) تقع ضمن UPG-1 + MEDIA وتتطلب جهازًا أو نشرًا. Q13–Q28 (عزل/موافقات/خزنات/اجتماعات/قواعد/Share) ضمن UPG-2 وما بعده.

الحالة الراهنة لجميع Q: **PENDING** (باستثناء اختبارات backend المصدرية أعلاه). لا PASS على الجهاز.
