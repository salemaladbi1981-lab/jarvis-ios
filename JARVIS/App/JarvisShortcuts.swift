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
                "كلّم \(.applicationName)"
            ],
            shortTitle: "Start Jarvis",
            systemImageName: "mic.fill"
        )

        AppShortcut(
            intent: JarvisOpenIntent(),
            phrases: [
                "Open \(.applicationName)",
                "Show \(.applicationName)",
                "افتح \(.applicationName)",
                "ورني \(.applicationName)"
            ],
            shortTitle: "Open Jarvis",
            systemImageName: "app.fill"
        )

    }
}
#endif
