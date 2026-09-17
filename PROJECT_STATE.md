# PROJECT_STATE — JARVIS V1.0 Live Baseline

> ملف الحالة الرسمي للمشروع. **اقرأه في بداية أي جلسة جديدة (`/new`)** لاستعادة السياق الكامل فوراً.

## Current Live Version
- **الاسم:** `JARVIS-V1.0-LIVE`
- **Release commit SHA:** `2f36cfbcb6e0009d1fd5d2ad2d87cf3304c744a2`
- **تاريخ الاعتماد:** 2026-09-17
- **الحالة:** **Live — مستقرة ومعتمدة.** Final Device Smoke Test على iPhone = PASS.
- **ملف التسليم المعتمد:** `JARVIS_V1_RC.zip` (project.pbxproj بصمة `12cae452081b5f53`).

## Frozen Baselines (نرجع إليها دائماً)
- `JARVIS-V1.0-LIVE` → commit `2f36cfb` (كود V1 النهائي + `KNOWN_ISSUES.md`).
- المعايرة السابقة: tag `m3.5-golden-baseline`.

## Device-verified PASS (iPhone — Final Smoke Test)
- ✅ Live Voice — يعمل.
- ✅ Barge-in — ممتاز.
- ✅ محادثة طبيعية — مع المالك ومع شخص آخر.
- ✅ Scroll/Touch أثناء الكلام — لا يقطع الكلام.
- ✅ Notifications — لا توقف المحادثة.
- ✅ الأصوات الجانبية — لا تلغي الرد.
- ✅ Calendar/Reminders — ضمن النسخة (EventKit حقيقي + توجيه `runCalendar`/`runReminders`) — regression مصدري PASS.

## Known Issues (غير مانعة للإطلاق)
- **Core Motion:** النواة لا تُظهر الحركة البصرية المرجوة على الجهاز. **مؤجلة إلى V1.1.** التشخيص الكامل في `KNOWN_ISSUES.md`.

## Frozen — لا تُعدَّل بدون regression مثبت + موافقة المالك
`AEC · PCM · Playback · Barge-in · WSS · verse · persona · VAD · Core Motion`

## Next Phase — V1.1 (مقترح، غير منفّذ)
1. Core Motion — إكمال الحركة البصرية للنواة.
2. Accessibility — Reduced Motion + VoiceOver.
3. iPad true landscape.
4. Real EventKit read — تحقق نهائي على الجهاز + صقل.
5. Offline mode.
6. persona/VAD/verse — refinements (بعد regression + موافقة المالك).

## قرار المالك
اعتماد JARVIS V1.0 كنسخة Live مستقرة نرجع إليها دائماً، والتطوير فوقها (V1.1+) دون المخاطرة بالنسخة العاملة.
