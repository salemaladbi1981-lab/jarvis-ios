# JARVIS — TestFlight Launch Checklist

آخر مراجعة: 2026-09-17 · الحالة: **READY** (لا blockers كودية متبقية)

## ✅ جاهز تقنياً (مُنجز + CI أخضر)
- Full Regression: Tools (291) + backend (136) — كلها PASS.
- App Intent / App Shortcut (استدعاء من قفل الشاشة) + Maps (search/distance/ETA/navigation handoff + App Intent).
- CI iOS + macOS + Swift tests — خضراء.
- `testflight.yml` (archive → export → upload) جاهز، gated على أسرار التوقيع.

## ⚠️ متبقٍ غير Apple (يكمله المالك)
1. **App Icon** — `JARVIS/Assets.xcassets/AppIcon.appiconset/AppIcon.png` حالياً placeholder (ذهبي على داكن). استبدله بالأيقونة الحقيقية 1024×1024 قبل الرفع.
2. **Privacy Policy URL** — مطلوب في App Store Connect (رابط سياسة خصوصية مستضاف).
3. **App Store Connect metadata** — الاسم، الوصف، التصنيف، الكلمات المفتاحية، اللقطات (الـ CI يولّد screenshots جاهزة).

## الخطوات فور تفعيل عضوية Apple
1. Apple Developer → إنشاء **App ID** `com.salemai.jarvis` + **Distribution Certificate** + **App Store Provisioning Profile**.
2. App Store Connect → إنشاء الـ app record `com.salemai.jarvis` + metadata + Privacy URL.
3. App Store Connect → إنشاء **App Store Connect API Key** (Admin) للرفع.
4. GitHub → Settings → Secrets → Actions:
   - `APPLE_DISTRIBUTION_CERTIFICATE_B64` (`.p12` Base64)
   - `APPLE_DISTRIBUTION_CERTIFICATE_PASSWORD`
   - `APPLE_PROVISIONING_PROFILE_B64`
   - `APPLE_TEAM_ID`
   - `ASC_API_KEY_ID` · `ASC_API_KEY_ISSUER_ID` · `ASC_API_KEY_B64`
5. GitHub Actions → **TestFlight Upload** → Run workflow → أول build ينرفع.

## مجمّد — لا يُعدَّل
Golden Voice · Barge-in · Memory · Calendar/Reminders · Email · Telegram · YouTube · Instagram · Realtime Tool Orchestration · Grounded Tool Contract.
