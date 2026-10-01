// swift-tools-version: 5.9
import PackageDescription

// Shared transport tests run without app signing or a simulator.
let package = Package(
    name: "JarvisTransport",
    platforms: [.macOS(.v14)],
    products: [.library(name: "JarvisTransport", targets: ["JarvisTransport"])],
    targets: [
        .target(name: "JarvisTransport", path: "JARVIS/Workspace",
                exclude: ["AttachmentMenu.swift", "AttachmentPreviewBar.swift", "AttachmentView.swift",
                          "AudioRecorderView.swift", "ConversationListView.swift", "ConversationView.swift",
                          "DeliveriesView.swift", "DetailViews.swift", "DocumentScanner.swift", "HomeEntryView.swift",
                          "InboxView.swift", "TasksView.swift", "WorkspaceComposerView.swift"],
                sources: ["JarvisAPI.swift", "WorkspaceModels.swift", "ChatViewModel.swift"]),
        .target(name: "JarvisProviders", path: "JARVIS", exclude: ["Agents", "App", "Assets", "Assets.xcassets", "Auth", "Camera", "Cards", "Core", "DesignSystem", "Diagnostics", "Home", "Info.plist", "Integrations", "Memory", "Notifications", "Providers", "Resources", "Upload", "Voice", "Workspace", "iPad", "macOS", "Mocks/MockData.swift"],
                sources: ["Mocks/MockProviders.swift", "State/JarvisState.swift"]),
        .testTarget(name: "JarvisTransportTests", dependencies: ["JarvisTransport", "JarvisProviders"], path: "Tests/Transport")
    ]
)
