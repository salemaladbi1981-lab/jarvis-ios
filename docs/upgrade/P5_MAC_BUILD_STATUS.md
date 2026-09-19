# P5 — mac build status: PRE-EXISTING / NON-P5 BLOCKER

## الخلاصة
فشل build الـmacOS (`JARVIS Mac` target) **قائم سابقًا على baseline UPG-2-LIVE** ولا يخص ملفات P5.

## الدليل
- ملفات UIKit-only التالية **موجودة في UPG-2-LIVE (0d6eb831)** وتستورد UIKit/VisionKit/AVKit بدون guard:
  - `JARVIS/Workspace/DocumentScanner.swift` (VisionKit: `VNDocumentCameraViewController`)
  - `JARVIS/Camera/CameraVideoView.swift` (AVKit: `AVPlayerViewController`)
  - `JARVIS/Camera/CameraCaptureView.swift` (UIKit: `UIImage`/`UIView`)
  - `JARVIS/Home/HomeView.swift` (UIKit)
  - `JARVIS/App/AppDelegate.swift` (UIKit: `UIApplicationDelegate`)
- الـ`mac_target` (يشارك `app_sources_phase` = كل APP_SOURCES) **موجود في generate_project.py منذ UPG-2-LIVE** (6 occurrences).
- ملفات P5 الجديدة تستورد **صفر UIKit** (فحص `grep "import UIKit"` = 0 عبر RootView/TasksView/ChatViewModel/ConversationView/ConversationListView/InboxView/DetailViews/HomeEntryView/WorkspaceModels/DeepLinkHandler).

## السبب الجذري
`mac_target` يبني نفس مصادر target الـiOS (`app_sources_phase`)، فيشمل ملفات UIKit-only التي لا تُترجم على macOS.

## الحل المقترح (منفصل عن P5 — refactor cross-platform)
1. `mac_sources_phase` يستبعد ملفات iOS-only (الكاميرا/المسح/HomeView/AppDelegate).
2. أو guard بـ `#if os(iOS)` داخل الملفات المشتركة (HomeViewModel/AdaptiveRootView/AudioCapture محروسة أصلًا).
3. هذا refactor واسع وليس من نطاق P5 (واجهة iOS).

## القرار
- **PRE-EXISTING / NON-P5 BLOCKER** — لا يُعتبر regression من P5.
- لا يؤخر P5. يُعالج كمهمة منفصلة.
