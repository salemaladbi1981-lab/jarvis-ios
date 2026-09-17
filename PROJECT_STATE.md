# PROJECT_STATE — JARVIS

> ملف الحالة الرسمي للمشروع. **اقرأه في بداية أي جلسة جديدة (`/new`)** لاستعادة السياق الكامل فوراً.

## Current Live Version
- **الاسم:** `JARVIS-V1.1-MULTI-EMAIL-LIVE`
- **Release commit SHA:** `ed2d03ab21e25c44a0a064969d0402d6df89a066`
- **تاريخ الاعتماد:** 2026-09-17
- **الحالة:** **Live — مستقرة ومعتمدة.** Physical iPhone Test = PASS.
- **ملف التسليم:** `JARVIS_V1.1_MULTI_EMAIL_DEVICE_TEST_FINAL.zip`

## Rollback Baselines (نرجع إليها عند الحاجة)
- `JARVIS-V1.1-MULTI-EMAIL-LIVE` → `ed2d03a` — Multi-Provider Email (Gmail + Hotmail) + Dynamic Account Grounding.
- `JARVIS-V1.1-PHASE2-LIVE` → `7dd7921` — Realtime Function Calling + Gmail حقيقي + Grounded Tool Contract.
- `JARVIS-V1.1-PHASE1-LIVE` → `75f0034` — Memory architecture + Real Tools (Calendar/Reminders).
- `JARVIS-V1.0-LIVE` → `2f36cfb` — Golden Voice + Barge-in + الواجهة. **لم يُلمس.**
- المعايرة السابقة: `m3.5-golden-baseline`.

## Device-verified PASS (iPhone)
### V1.1 Multi-Email (النسخة الحالية)
- ✅ **Multi-Provider Email** — Gmail + Hotmail (Microsoft Graph).
- ✅ Read · Grounding (بدون اختراع) · Reply · Confirmation · Send · Sent verification = PASS.
- ✅ Dynamic Account Grounding — قائمة الحسابات الحقيقية محقونة في وصف الأدوات (لا تخمين account_id).
- ✅ account_not_found لأي حساب غير موجود (لا fallback فارغ).
- ✅ Unified Inbox + تمييز كل رسالة بـ account_id + provider.
- ✅ Cross-account safety — الإرسال من الحساب الصحيح فقط.
- ✅ Live Voice + Barge-in محفوظان.

### V1.1 Phase 2 (سابقة — تبقى صالحة)
- ✅ Realtime Function Calling · Gmail Read/Summary/Search · Grounding · Confirmation · Send بـ sent ID حقيقي.

### V1.1 Phase 1 (سابقة — تبقى صالحة)
- ✅ Personal Memory · المشاريع/القرارات · Calendar · Reminders + التأكيد.

### V1.0 (سابقة — تبقى صالحة)
- ✅ Live Voice · Barge-in · محادثة طبيعية · Scroll/Touch · Notifications · الأصوات الجانبية.

## Frozen — لا تُعدَّل بدون regression مثبت + موافقة المالك
- **Golden Voice** · **Barge-in** · **Memory** · **Calendar/Reminders**
- **Email (Gmail + Hotmail)** · **Realtime Tool Orchestration** · **Grounded Tool Contract**
- `AEC · PCM · Playback · WSS · verse · persona · VAD · Core Motion`

## Grounded Tool Contract (baseline إلزامي لكل الأدوات القادمة)
- أي ادعاء يعتمد على بيانات أداة لا يُقبل إلا من نتيجة الأداة الحالية (لا hallucination).
- كل عنصر يرتبط بمعرّف حقيقي (message_id / account_id / …).
- الإرسال confirmation-required؛ success فقط بعد provider API success + معرّف حقيقي.
- كل أداة قادمة ترث نفس contract + نفس دورة Realtime Function Calling.

## Known Issues (غير مانعة)
- **Core Motion** — غير مكتملة بصرياً، مؤجلة (قرار المالك: بعد الإطلاق).

## Next Phase (الأولوية القادمة)
- **Telegram Personal Account integration** — ثم WhatsApp feasibility → YouTube → Instagram → Web/Search → Files/Documents → Device Control.
- كلها عبر نفس Realtime Function Calling + Grounded Tool Contract.

## قرار المالك
اعتماد V1.1 Multi-Email (Gmail + Hotmail) كـ stable Live baseline، وتجميد البريد (لا تعديل إضافي). التالي: Telegram.
