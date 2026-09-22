import SwiftUI

#if os(macOS)
import AppKit

/// Launch activation belongs to the application lifecycle rather than a SwiftUI
/// view's first render. Deferring one main-run-loop turn lets WindowGroup finish
/// creating its NSWindow before we make that exact window key and frontmost.
final class MacApplicationDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)
            NSApp.windows.first(where: { $0.canBecomeKey })?.makeKeyAndOrderFront(nil)
        }
    }
}

@main
struct MacApp: App {
    @NSApplicationDelegateAdaptor(MacApplicationDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            AdaptiveRootView()
                .environment(\.layoutDirection, .rightToLeft)
                .preferredColorScheme(.dark)
                .frame(minWidth: 1000, minHeight: 640)
        }
    }
}
#endif
