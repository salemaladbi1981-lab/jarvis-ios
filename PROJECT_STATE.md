# PROJECT_STATE — JARVIS

> ملف الحالة الرسمي للمشروع. **اقرأه في بداية أي جلسة جديدة (`/new`)** لاستعادة السياق الكامل فوراً.

## Current Live Version
- **الاسم:** `JARVIS-V1.1-TELEGRAM-LIVE`
- **Release commit SHA:** `006bb41d5a0271c3e7adaedbd90961078106a78e`
- **تاريخ الاعتماد:** 2026-09-17
- **الحالة:** **Live — مستقرة ومعتمدة.** Physical iPhone Test = PASS.
- **ملف التسليم:** `JARVIS_V1.1_TELEGRAM_DEVICE_TEST_FINAL.zip`

## Rollback Baselines (نرجع إليها عند الحاجة)
- `JARVIS-V1.1-TELEGRAM-LIVE` → `006bb41` — Telegram Personal Account (Search/Read/Draft/Reply/Confirmation/Send).
- `JARVIS-V1.1-MULTI-EMAIL-LIVE` → `ed2d03a` — Multi-Provider Email (Gmail + Hotmail) + Dynamic Account Grounding.
- `JARVIS-V1.1-PHASE2-LIVE` → `7dd7921` — Realtime Function Calling + Gmail + Grounded Tool Contract.
- `JARVIS-V1.1-PHASE1-LIVE` → `75f0034` — Memory + Calendar/Reminders.
- `JARVIS-V1.0-LIVE` → `2f36cfb` — Golden Voice + Barge-in + الواجهة. **لم يُلمس.**
- المعايرة السابقة: `m3.5-golden-baseline`.

## Device-verified PASS (iPhone)
### V1.1 Telegram (النسخة الحالية)
- ✅ **Telegram Personal Account** — حساب شخصي (MTProto/telethon).
- ✅ Search · تحديد الرسالة · Read = PASS على الجهاز.
- ✅ Draft · Reply · Confirmation · Send = PASS فعلياً.
- ✅ peer_id → chat_id آمن (PeerUser/PeerChannel/PeerChat).
- ✅ نفس Grounded Tool Contract + confirmation.

### V1.1 Multi-Email (سابقة — تبقى صالحة)
- ✅ Multi-Provider Email (Gmail + Hotmail) · Unified Inbox · Dynamic Account Grounding · cross-account safety.

### V1.1 Phase 2 / Phase 1 / V1.0 (سابقة — تبقى صالحة)
- ✅ Realtime Function Calling · Gmail · Memory · Calendar/Reminders · Golden Voice · Barge-in.

### V1.1 YouTube
- ✅ `youtube_search` · `youtube_details` · `youtube_transcript` (بحث/تفاصيل/تفريغ).
- ✅ `youtube_play` — Playback Handoff بدون OAuth: يفتح الفيديو في تطبيق YouTube الرسمي (DEVICE PASS).
- ⏸ OAuth للقناة معلّق مؤقتاً بقرار المالك (invalid_client سابقاً — credentials تُعاد لاحقاً).

### V1.1 Instagram
- ✅ `instagram_profile` · `instagram_insights` · `instagram_recent_media` (Meta Graph API read).
- ✅ تحقق حيّاً: 99,848 متابع · reach 7d · media حقيقي (media_id).
- ⏸ publish / messaging = blocker خارجي (App Review / business verification).

## Frozen — لا تُعدَّل بدون regression مثبت + موافقة المالك
- **Golden Voice** · **Barge-in** · **Memory** · **Calendar/Reminders**
- **Email (Gmail + Hotmail)** · **Telegram** · **Realtime Tool Orchestration** · **Grounded Tool Contract**
- `AEC · PCM · Playback · WSS · verse · persona · VAD · Core Motion`

## Grounded Tool Contract (baseline إلزامي لكل الأدوات القادمة)
- أي ادعاء يعتمد على بيانات أداة لا يُقبل إلا من نتيجة الأداة الحالية (لا hallucination).
- كل عنصر يرتبط بمعرّف حقيقي (message_id / chat_id / account_id / …).
- الإرسال confirmation-required؛ success فقط بعد provider API success + معرّف حقيقي.
- كل أداة قادمة ترث نفس contract + نفس دورة Realtime Function Calling.

## Known Issues (غير مانعة)
- **Core Motion** — غير مكتملة بصرياً، مؤجلة (قرار المالك: بعد الإطلاق).

## Next Phase (الأولوية القادمة)
- **WhatsApp** — ثم Web/Search → Files/Documents → Device Control.
- كلها عبر نفس Realtime Function Calling + Grounded Tool Contract.

## قرار المالك
اعتماد V1.1 YouTube + Instagram كـ stable. التالي: WhatsApp (Cloud API).
