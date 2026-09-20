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
        .testTarget(name: "JarvisTransportTests", dependencies: ["JarvisTransport"], path: "Tests/Transport")
    ]
)
