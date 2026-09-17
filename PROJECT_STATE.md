# PROJECT_STATE — JARVIS

> ملف الحالة الرسمي للمشروع. **اقرأه في بداية أي جلسة جديدة (`/new`)** لاستعادة السياق الكامل فوراً.

## Current Live Version
- **الاسم:** `JARVIS-V1.1-PHASE2-LIVE`
- **Release commit SHA:** `7dd7921d911243b35f06be16ddb22a8bddbd30e1`
- **تاريخ الاعتماد:** 2026-09-17
- **الحالة:** **Live — مستقرة ومعتمدة.** Physical iPhone Test = PASS.
- **ملف التسليم:** `JARVIS_V1.1_PHASE2_DEVICE_TEST_FINAL.zip` (الكود الأساسي `f6bd5d4`)

## Rollback Baselines (نرجع إليها عند الحاجة)
- `JARVIS-V1.1-PHASE2-LIVE` → `7dd7921` — V1.1 Phase 2: Realtime Function Calling + Gmail حقيقي + Grounded Tool Contract.
- `JARVIS-V1.1-PHASE1-LIVE` → `75f0034` — V1.1 Phase 1: Memory architecture + Real Tools (Calendar/Reminders write).
- `JARVIS-V1.0-LIVE` → `2f36cfb` — V1.0: Golden Voice + Barge-in + الواجهة. **لم يُلمس — نقطة رجوع سابقة.**
- المعايرة السابقة: `m3.5-golden-baseline`.

## Device-verified PASS (iPhone)
### V1.1 Phase 2 (النسخة الحالية)
- ✅ Gmail الحقيقي متصل (Read/Summary/Search).
- ✅ Grounding — بدون اختراع رسائل (كل ادعاء مربوطة بـ message_id حقيقي).
- ✅ Realtime Function Calling — دورة واحدة: صوت → tool call → Gmail → نتيجة → نفس المحادثة → جواب واحد.
- ✅ متابعة نفس الرسالة («اقرأ الأول» → «رد عليه» → «أرسل»).
- ✅ Draft/Reply على message_id حقيقي.
- ✅ Confirmation قبل الإرسال (لا إرسال بدون تأكيد صريح).
- ✅ Email Send = PASS — الرسالة ظهرت فعلياً في Gmail Sent بـ sent message ID حقيقي.
- ✅ Live Voice + Barge-in محفوظان.

### V1.1 Phase 1 (سابقة — تبقى صالحة)
- ✅ Personal Memory · استرجاع المشاريع/القرارات · Calendar (قراءة) · إنشاء Reminder + التأكيد · Live Voice · Barge-in.

### V1.0 (سابقة — تبقى صالحة)
- ✅ Live Voice · Barge-in · محادثة طبيعية · Scroll/Touch · Notifications · الأصوات الجانبية.

## Frozen — لا تُعدَّل بدون regression مثبت + موافقة المالك
- **Golden Voice** · **Barge-in** · **Memory architecture** · **Calendar/Reminders integration**
- **Gmail / Realtime Tool Orchestration** · **Grounded Tool Contract**
- `AEC · PCM · Playback · WSS · verse · persona · VAD · Core Motion`

## Grounded Tool Contract (baseline إلزامي لكل الأدوات القادمة)
- أي ادعاء يعتمد على بيانات أداة لا يُقبل إلا إذا كانت موجودة في نتيجة الأداة الحالية.
- Tool failure / empty → يقول بوضوح «لم أجد / تعذر الوصول»، ممنوع hallucinated fallback.
- كل عنصر (رسالة/مستند/رسالة دردشة) يرتبط بمعرّف حقيقي من ToolResult.
- **Gmail Send لا يُعتبر success إلا بعد Gmail API success + sent message ID حقيقي.**
- الإرسال confirmation-required دائماً؛ بعد النجاح يُمسح pending draft (لا إرسال مزدوج).
- كل أداة قادمة (Telegram/WhatsApp/Web/Search/Files) ترث نفس contract بنفس دورة Realtime Function Calling.

## Known Issues (غير مانعة)
- **Core Motion** — غير مكتملة بصرياً، مؤجلة (قرار المالك: بعد الإطلاق).

## Next Phase (مقترح — غير منفّذ)
الترتيب: Telegram → WhatsApp feasibility → YouTube → Instagram → Web/Search → Files/Documents → Device Control.
كلها عبر نفس Realtime Function Calling + Grounded Tool Contract المثبت الآن.

## قرار المالك
اعتماد V1.1 Phase 2 كـ stable Live baseline فوق Phase 1 وV1.0، مع الحفاظ على نقاط الرجوع السابقة دون أي تغيير.
