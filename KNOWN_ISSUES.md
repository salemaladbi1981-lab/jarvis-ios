# JARVIS V1 — Known Issues (غير مانعة للإطلاق)

## قرار المالك — تجميد
Core Motion **مؤجلة لما بعد V1 Live**. لا محاولات إصلاح إضافية الآن. يُعاد فتحها بعد الإطلاق فقط.

## الحالة المثبتة على iPhone (Final Device QA — PASS)
- Live Voice يعمل.
- Barge-in يعمل.
- الأصوات الجانبية لا تلغي الرد في آخر اختبار.
- Notification لا يوقف المحادثة في آخر اختبار.
- Scroll/Touch لا يقطع الكلام.

## Known Issue #1 — Core Motion (النواة لا تظهر الحركة المطلوبة على الجهاز)
- **الوصف:** النواة (الـ orb الحي) لا تُظهر الحركة المرجوة على الجهاز الفعلي رغم أن الحركة مشتقة من runtime state + audio levels (RMS → perceptual).
- **التصنيف:** بصري/تجميلي فقط — لا يمس أي وظيفة أساسية (صوت، barge-in، تنقّل، صلاحيات، بيانات).
- **الحكم:** غير مانع للإطلاق (Non-blocking). مجمّد.

## ما لا يُعاد فتحه (قرار المالك)
AEC · PCM · Playback · WSS · verse · persona · VAD · Core Motion.

## تشخيص محفوظ للعودة بعد الإطلاق
الحركة مبنية على طبقة قابلة للضبط مركزيًا — العودة تكون بضبط القيم فقط، لا بتغيير المعمارية:
- `JARVIS/Core/MotionTokens.swift` — كل القيم المركزية:
  - `Amplitude.listening = 0.25` / `speaking = 0.18` (نسب من radius).
  - `Smoothing.attackAlpha = 0.55` / `releaseAlpha = 0.18` (EMA مباشر في Core onChange).
  - `Level.perceptual(_:)` — gain = 8.0 (يرفع RMS الصغير 0.02–0.3 إلى مدى مرئي، يشبع عند 1.0).
- `JARVIS/Core/JarvisCoreView.swift` — الـ Canvas المشتق من state + micP/outP.
- `JARVIS/Core/VisualLevelModel.swift` — عزل RMS في نموذج خفيف (لا تلمس HomeViewModel عند العودة).
- `JARVIS/Core/WaveformView.swift` — waveform مدفوع بـ perceptual level.

### ملاحظات تشخيصية محفوظة
- العزل الصحيح موجود: مستويات RMS في `VisualLevelModel` (lightweight) وليست `@Published` في `HomeViewModel` — لا إعادة رندر كاملة للشاشة.
- `frameTimeMs` غير قابل للملاحظة (non-observable) — لا حلقة إعادة رندر.
- لا تعديل `@State` داخل Canvas render closure (سبب crash سابق — مُصلح ومُثبَّت بالاختبار).
