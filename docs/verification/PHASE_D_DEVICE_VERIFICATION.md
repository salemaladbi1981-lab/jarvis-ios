# PHASE D — Device Verification Checklist

> **قاعدة:** لا يُغيَّر أي status إلى VERIFIED إلا بعد اختبار فعلي على الجهاز.
> قبل البدء: `git checkout feat/master-build-v1` + build نظيف على Xcode.

---

## Mac Requirements
- macOS 14+ (Sonoma) أو أحدث.
- Xcode 15.3+ (Swift 5.9+ — مطلوب `@Observable`, async/await, `@UIApplicationDelegateAdaptor`).
- Apple Developer account (لتوقيع التطبيق على الجهاز).
- الوصول إلى `https://jarvis-api.qeyas.app` (شبكة) + السيرفر live.
- توليد enrollment code من السيرفر (بواسطة جلسة المالك): `POST /auth/enroll/code`.

## iPhone Requirements
- iPhone فعلي (ليس Simulator) — مطلوب لاختبارات: الكاميرا front/rear + flash، تسجيل الفيديو + الميكروفون، background upload، Keychain persistence بعد relaunch، network interruption.
- iOS 17+.
- ملف توقيع صالح + الجهاز مضاف لـ developer portal.

## Test Order
1. Build (1–2)
2. Enrollment + Keychain (3–4)
3. Camera (5–10)
4. Media pickers (11–12)
5. Upload (13–17)
6. Inbox/Task/Delivery (18–21)
7. Security regression (22)
8. Realtime/background regression (23–24)

---

# Checklist (24)

| # | Test | Expected | Actual | P/F | Evidence |
|---|------|----------|--------|-----|----------|
| 1 | Clean Build | Product → Clean Build Folder يعمل بلا أخطاء |  |  | لقطة Xcode |
| 2 | Compile warnings/errors | صفر errors، ولا warnings حرجة |  |  | Build log |
| 3 | Pairing enrollment | إدخال code صحيح → `isEnrolled=true` + دخول الشاشة الرئيسية؛ code خاطئ → رسالة رفض |  |  | لقطة UI + سجل `/auth/enroll` |
| 4 | Keychain persistence after relaunch | بعد قتل التطبيق وإعادة فتحه، session_token يبقى (لا يعيد طلب enrollment) |  |  | لقطة + سجل |
| 5 | Camera photo | التقاط صورة حقيقية من الكاميرا |  |  | صورة |
| 6 | Front/rear camera | التبديل front↔rear يعمل (input القديم يُزال) بلا crash |  |  | صورة (الوجهين) |
| 7 | Flash | تشغيل/إطفاء الفلاش على الخلفية |  |  | صورة بفلاش/بدون |
| 8 | Photo preview + Retake + Use | بعد الالتقاط: معاينة + Retake يلتقط من جديد + Use يُرفع فقط بعد الموافقة |  |  | لقطات |
| 9 | Video recording + mic | تسجيل فيديو مع صوت الميكروفون (start/stop) |  |  | فيديو + صوت |
| 10 | Video preview + Retake + Use | معاينة الفيديو المسجل + Retake + Use يحفظ الأصل |  |  | فيديو |
| 11 | Photo Library | اختيار صورة من المكتبة + إذن NSPhotoLibrary |  |  | لقطة |
| 12 | File picker | اختيار ملف (PDF/DOCX/…) من Files |  |  | لقطة |
| 13 | Large file upload | رفع ملف كبير (≥10MB) chunked بلا خطأ + progress |  |  | log + progress |
| 14 | Kill app during upload | قتل التطبيق أثناء الرفع لا يفسد upload_id |  |  | log |
| 15 | Relaunch + resume same upload_id | إعادة فتح التطبيق → يستأنف نفس upload_id (لا init جديد) |  |  | سجل server (upload_id ثابت) |
| 16 | Background upload | الرفع يكمل والتطبيق في الخلفية (handleEventsForBackgroundURLSession) |  |  | سجل |
| 17 | Network interruption + recovery | قطع الشبكة ثم عودتها → يستأنف الأجزاء الناقصة فقط |  |  | سجل (GET status) |
| 18 | Inbox loads real files | GET /files يظهر الملفات المرفوعة فعلًا |  |  | لقطة + JSON |
| 19 | Task creation | إنشاء task مربوط بالمرفق → task_id + status=uploaded |  |  | JSON |
| 20 | Delivery appears | بعد المعالجة delivery يظهر في التسليمات |  |  | لقطة |
| 21 | Open/download/share Delivery | فتح/تنزيل/مشاركة ملف التسليم يعمل |  |  | لقطة |
| 22 | Cross-user/security regression | user آخر (بلا session/بـ session غيره) يُرفض 401/forbidden على كل files/tasks/deliveries |  |  | سجل 401 |
| 23 | Voice/Realtime regression | المحادثة الصوتية + function calling ما تزال تعمل (لا تأثير من Phase D) |  |  | تسجيل صوتي |
| 24 | App background/foreground regression | الخروج/العودة لا يكسر الصوت ولا الرفع |  |  | لقطة |

---

## ملاحظات النتيجة
- كل بند لا يُمرَّر إلا بـ PASS فعلي + دليل (لقطة/سجل).
- أي UNVERIFIED يبقى UNVERIFIED حتى Device Verification.
