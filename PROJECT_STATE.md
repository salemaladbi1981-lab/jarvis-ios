# PROJECT_STATE — JARVIS

> ملف الحالة الرسمي للمشروع. **اقرأه في بداية أي جلسة جديدة (`/new`)** لاستعادة السياق الكامل فوراً.

## Current Live Version
- **الاسم:** `JARVIS-V1.1-PHASE1-LIVE`
- **Release commit SHA:** `75f00348cc598d3d976e3b3ffdc2b2679728d448`
- **تاريخ الاعتماد:** 2026-09-17
- **الحالة:** **Live — مستقرة ومعتمدة.** Physical iPhone Test = PASS.
- **ملف التسليم:** `JARVIS_V1.1_PHASE1_75f0034.zip`

## Rollback Baselines (نرجع إليها عند الحاجة)
- `JARVIS-V1.1-PHASE1-LIVE` → `75f0034` — V1.1 Phase 1: Memory architecture + Real Tools (Calendar/Reminders write).
- `JARVIS-V1.0-LIVE` → `2f36cfb` — V1.0: Golden Voice + Barge-in + الواجهة. **لم يُلمس — نقطة رجوع سابقة.**
- المعايرة السابقة: `m3.5-golden-baseline`.

## Device-verified PASS (iPhone)
### V1.1 Phase 1 (النسخة الحالية)
- ✅ Personal Memory — استرجاع معلومات المالك.
- ✅ استرجاع سياق المشاريع/القرارات.
- ✅ Calendar (قراءة).
- ✅ إنشاء Reminder + التأكيد.
- ✅ Live Voice.
- ✅ Barge-in regression.

### V1.0 (سابقة — تبقى صالحة)
- ✅ Live Voice · Barge-in · محادثة طبيعية · Scroll/Touch · Notifications · الأصوات الجانبية.

## Frozen — لا تُعدَّل بدون regression مثبت + موافقة المالك
- **Golden Voice الحالي** · **Barge-in** · **Memory architecture** · **Calendar/Reminders integration**
- `AEC · PCM · Playback · WSS · verse · persona · VAD · Core Motion`

## Known Issues (غير مانعة)
- **Core Motion** — غير مكتملة بصرياً، مؤجلة.

## Next Phase (مقترح — غير منفّذ)
التقييم بالترتيب: Email → Files/Documents → Web/Search → Travel/Bookings → Specialized Agents → Device/Home control. (التفصيل في تسليم الجلسة.)

## قرار المالك
اعتماد V1.1 Phase 1 كـ stable baseline جديد فوق V1.0، مع الحفاظ على V1.0 كنقطة رجوع سابقة دون أي تغيير.
