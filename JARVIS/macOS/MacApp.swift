import SwiftUI

#if os(macOS)
import AppKit

@main
struct MacApp: App {
    var body: some Scene {
        WindowGroup {
            AdaptiveRootView()
                .environment(\.layoutDirection, .rightToLeft)
                .preferredColorScheme(.dark)
                .frame(minWidth: 1000, minHeight: 640)
                .onAppear {
                    // A normal desktop app must own a visible, switchable window.
                    // Keep this local to macOS: no Accessibility/Automation permission
                    // is requested here and no external application is controlled.
                    NSApp.setActivationPolicy(.regular)
                    NSApp.activate(ignoringOtherApps: true)
                    NSApp.windows.first?.makeKeyAndOrderFront(nil)
                }
        }
    }
}
#endif
