#if os(iOS)
import AppIntents

/// App Shortcuts — عبارات Siri/Shortcuts لاستدعاء JARVIS.
struct JarvisShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: JarvisVoiceIntent(),
            phrases: [
                "Start \(.applicationName)",
                "Ask \(.applicationName)",
                "Talk to \(.applicationName)",
                "شغل \(.applicationName)",
                "اسأل \(.applicationName)",
                "افتح \(.applicationName)"
            ],
            shortTitle: "Start Jarvis",
            systemImageName: "mic.fill"
        )

        AppShortcut(
            intent: JarvisNavigateIntent(),
            phrases: [
                "Navigate with \(.applicationName)",
                "Directions with \(.applicationName)",
                "وديني عبر \(.applicationName)",
                "خذني عبر \(.applicationName)"
            ],
            shortTitle: "Navigate",
            systemImageName: "location.fill"
        )
    }
}
#endif
