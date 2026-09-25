import SwiftUI

#if os(macOS)
@main
struct MacApp: App {
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    private var isPreview: Bool {
        #if DEBUG
        return ProcessInfo.processInfo.arguments.contains("-demo")
            || JarvisConfig.injectedSessionToken != nil
        #else
        return false
        #endif
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if enrollment.isEnrolled || isPreview {
                    MacHomeView().id(enrollment.sessionToken)
                } else {
                    PairingView()
                }
            }
            .environmentObject(enrollment)
            .environment(\.layoutDirection, .rightToLeft)
            .preferredColorScheme(.dark)
            .frame(minWidth: 820, minHeight: 620)
        }
        .defaultSize(width: 1120, height: 820)
    }
}
#endif
