# JARVIS — Private TestFlight Checklist (أجهزة المالك فقط)

آخر مراجعة: 2026-09-17 · الحالة: **READY** (لا blockers كودية متبقية)

النشر: **Private TestFlight** — أجهزة د. سالم فقط (internal testers). لا App Store عام.

## ✅ جاهز تقنياً (مُنجز + CI أخضر)
- Full Regression: Tools (291) + backend (136) — كلها PASS.
- App Intent / App Shortcut (استدعاء من قفل الشاشة) + Maps (search/distance/ETA/navigation handoff + App Intent).
- CI iOS + macOS + Swift tests — خضراء.
- `testflight.yml` (archive → export → upload) جاهز، gated على أسرار التوقيع.

## ⚠️ متبقٍ غير Apple (يكمله المالك)
1. **App Icon** — `Assets.xcassets/AppIcon.appiconset/AppIcon.png` حالياً placeholder. استبدله بالأيقونة 1024×1024.
2. **App Store Connect**: إنشاء الـ app record (اسم + `com.salemai.jarvis`) فقط — **لا** metadata عامة (لا وصف/لقطات/كلمات) ولا Privacy URL (غير لازمة لـ internal TestFlight).

## الخطوات فور تفعيل عضوية Apple (Private TestFlight فقط)
1. Apple Developer → **App ID** `com.salemai.jarvis` + **Distribution Certificate** + **App Store Provisioning Profile**.
2. App Store Connect → إنشاء الـ app record (اسم + bundle ID).
3. App Store Connect → **App Store Connect API Key** (Admin) للرفع.
4. GitHub → Settings → Secrets → Actions:
   - `APPLE_DISTRIBUTION_CERTIFICATE_B64` (`.p12` Base64)
   - `APPLE_DISTRIBUTION_CERTIFICATE_PASSWORD`
   - `APPLE_PROVISIONING_PROFILE_B64`
   - `APPLE_TEAM_ID`
   - `ASC_API_KEY_ID` · `ASC_API_KEY_ISSUER_ID` · `ASC_API_KEY_B64`
5. GitHub Actions → **TestFlight Upload** → Run workflow → build ينرفع لـ TestFlight.
6. TestFlight → **Internal Testing** → أضف جهازك → ثبّت.

**لا App Review ولا Privacy Policy ولا metadata عامة مطلوبة** لـ internal TestFlight.

## مجمّد — لا يُعدَّل
Golden Voice · Barge-in · Memory · Calendar/Reminders · Email · Telegram · YouTube · Instagram · Realtime Tool Orchestration · Grounded Tool Contract.
