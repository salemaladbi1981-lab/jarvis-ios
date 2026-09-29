import SwiftUI

#if os(macOS)
@main
struct MacApp: App {
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    init() {
        // تشخيص: اجعل stdout بلا تخزين مؤقت حتى تظهر أسطر [JARVIS-TRACE] فوراً عند التشغيل من الطرفية.
        setvbuf(stdout, nil, _IONBF, 0)
        setvbuf(stderr, nil, _IONBF, 0)
    }

    /// -demo / -sessionToken: يفتح الواجهة بلا enrollment (للتطوير فقط).
    private var isDemo: Bool {
        ProcessInfo.processInfo.arguments.contains("-demo")
        || ProcessInfo.processInfo.arguments.contains("-sessionToken")
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if enrollment.isEnrolled || isDemo {
                    AdaptiveRootView()
                } else {
                    PairingView()
                }
            }
            .environmentObject(enrollment)
            .environment(\.layoutDirection, .rightToLeft)
            .preferredColorScheme(.dark)
            .frame(minWidth: 1000, minHeight: 640)
        }
    }
}
#endif
