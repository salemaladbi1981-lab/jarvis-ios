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
                "شغّل جارفس",
                "اسأل جارفس",
                "افتح جارفس",
            ],
            shortTitle: "Start Jarvis",
            systemImageName: "mic.fill"
        )
    }
}
#endif
