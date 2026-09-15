# JARVIS — Direct iPhone Install Status

## Build
- iOS: PASS (Xcode 15.4 CI — success)
- macOS: PASS (Xcode 15.4 CI — success)
- ملاحظة: البناء تم على Xcode 15.4؛ المالك سيستخدم Xcode 27 (أحدث، متوافق).

## Tests
- M3.2/M3.3 (orchestrator + approval): 23 PASS / 0 FAIL
- M3.4 (calendar/reminders): 13 PASS / 0 FAIL
- M3.1 (live harness): 14 PASS / 0 FAIL
- المجموع: 50 PASS / 0 FAIL

## Signing
- CODE_SIGN_STYLE = Automatic (Personal Team — لا Team ID خارجي).
- Bundle ID: com.salemai.jarvis (قابل للتغيير أثناء التوقيع المحلي).

## Privacy descriptions (مضافة داخل المشروع)
- Calendar: NSCalendarsUsageDescription
- Reminders: NSRemindersUsageDescription
- Microphone: NSMicrophoneUsageDescription

## بدون OPENAI_API_KEY
التطبيق يفتح طبيعياً، Live Voice يظهر "غير متاح" — لا crash.

## Deferred (Device Gate)
- Real EventKit read (بيانات تقويم/تذكيرات شخصية)
- Real mic + streaming + barge-in
- iPad true landscape, Reduced Motion, VoiceOver, offline
