import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

struct PendingAttachment: Identifiable {
    let id = UUID()
    let kind: String  // photo | video | file | scan | audio
    let data: Data?
    let url: URL?
    let filename: String
}

/// Single-column Home (iPhone + iPad portrait + narrow split view).
/// Reuses shared hero/title/waveform components.
struct HomeView: View {
    @StateObject private var vm = HomeViewModel()
    @EnvironmentObject private var enrollment: EnrollmentManager
    @State private var selectedTab = "home"
    @State private var composerText = ""
    @State private var showAttachments = false
    @State private var showCameraPhoto = false
    @State private var showCameraVideo = false
    @State private var pendingAttachments: [PendingAttachment] = []
    @State private var showPhotoPicker = false
    @State private var showVideoPicker = false
    @State private var photoItem: PhotosPickerItem?
    @State private var videoItem: PhotosPickerItem?
    @State private var showFileImporter = false
    @State private var showScanner = false
    @State private var showAudioRecorder = false
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: JarvisSpacing.lg) {
                    HeaderView()
                        .id("top")

                    JarvisHeroView(vm: vm)

                    JarvisTitleGreetingView()

                    JarvisWaveformStatusView(vm: vm)

                    SmartHomeCard(devices: vm.homeDevices)
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "read-temperature") }

                    SecurityCard(status: vm.securityStatus ?? SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true))
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "unlock-door") }

                    MediaCard(track: vm.mediaTrack ?? MediaTrack(title: "Blinding Lights", artist: "The Weeknd", current: "2:06", duration: "3:20"))

                    QuickSuggestions(commands: QuickCommand.productionCases) { cmd in
                        Task { await vm.handleQuickCommand(cmd) }
                    }

                    if let msg = vm.calendarMessage {
                        Text(msg)
                            .font(.system(size: 14))
                            .foregroundColor(JarvisColor.text_primary)
                            .padding(JarvisSpacing.md)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(RoundedRectangle(cornerRadius: JarvisRadius.card).fill(JarvisColor.bg_1.opacity(0.45)))
                            .overlay(RoundedRectangle(cornerRadius: JarvisRadius.card).stroke(JarvisColor.primary_blue.opacity(0.16), lineWidth: 1))
                    }

                    if let approval = vm.pendingApproval {
                        ApprovalCardView(vm: vm, action: approval)
                    }
                    Color.clear.frame(height: 1).id("bottom")
                }
                .padding(JarvisSpacing.lg)
            }
            .defaultScrollAnchor(.top)
            .onAppear {
                LaunchTiming.mark("home onAppear")
                if ProcessInfo.processInfo.arguments.contains("-scrollBottom") {
                    proxy.scrollTo("bottom", anchor: .bottom)
                } else {
                    // cold launch / re-entry → النواة فوق الـ fold دائماً
                    proxy.scrollTo("top", anchor: .top)
                }
            }
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 0) {
                AttachmentPreviewBar(attachments: pendingAttachments) { id in
                    pendingAttachments.removeAll { $0.id == id }
                }
                WorkspaceComposerView(
                    text: $composerText,
                    onSend: {
                        let t = composerText.trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !t.isEmpty || !pendingAttachments.isEmpty else { return }
                        composerText = ""
                        Task { await sendMessage(text: t) }
                    },
                    onAttach: { showAttachments = true },
                    onMic: { vm.toggleVoice() }
                )
                .padding(.horizontal, JarvisSpacing.lg)
                BottomNavBar(selected: $selectedTab)
            }
        }
        .background(
            LinearGradient(colors: [JarvisColor.bg_0, JarvisColor.bg_1], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
        )
        .task {
            await vm.load()
            vm.handleAppIntentStart()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { vm.handleAppBackgrounded() }
        }
        .sheet(isPresented: $showAttachments) {
            AttachmentMenu(
                onPickPhotos: { showAttachments = false; showPhotoPicker = true },
                onPickVideos: { showAttachments = false; showVideoPicker = true },
                onPickFiles: { showAttachments = false; showFileImporter = true },
                onCameraPhoto: {
                    showAttachments = false
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { showCameraPhoto = true }
                },
                onCameraVideo: {
                    showAttachments = false
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { showCameraVideo = true }
                },
                onScanDocument: { showAttachments = false; showScanner = true },
                onRecordAudio: { showAttachments = false; showAudioRecorder = true }
            )
        }
        .fullScreenCover(isPresented: $showCameraPhoto) {
            CameraCaptureView { data, mime in
                pendingAttachments.append(PendingAttachment(kind: "photo", data: data, url: nil, filename: "photo-\(UUID().uuidString).jpg"))
            }
        }
        .fullScreenCover(isPresented: $showCameraVideo) {
            CameraVideoView { url in
                pendingAttachments.append(PendingAttachment(kind: "video", data: nil, url: url, filename: url.lastPathComponent))
            }
        }
        .photosPicker(isPresented: $showPhotoPicker, selection: $photoItem, matching: .images)
        .onChange(of: photoItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self) {
                    pendingAttachments.append(PendingAttachment(kind: "photo", data: data, url: nil, filename: "photo-\(UUID().uuidString).jpg"))
                }
            }
        }
        .photosPicker(isPresented: $showVideoPicker, selection: $videoItem, matching: .videos)
        .onChange(of: videoItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self) {
                    pendingAttachments.append(PendingAttachment(kind: "video", data: data, url: nil, filename: "video-\(UUID().uuidString).mov"))
                }
            }
        }
        .fileImporter(isPresented: $showFileImporter, allowedContentTypes: [.item]) { result in
            if case .success(let url) = result {
                let data = try? Data(contentsOf: url)
                pendingAttachments.append(PendingAttachment(kind: "file", data: data, url: url, filename: url.lastPathComponent))
            }
        }
        .fullScreenCover(isPresented: $showScanner) {
            DocumentScanner { urls in
                for url in urls {
                    let data = try? Data(contentsOf: url)
                    pendingAttachments.append(PendingAttachment(kind: "scan", data: data, url: url, filename: url.lastPathComponent))
                }
            }
        }
        .fullScreenCover(isPresented: $showAudioRecorder) {
            AudioRecorderView { url in
                pendingAttachments.append(PendingAttachment(kind: "audio", data: nil, url: url, filename: url.lastPathComponent))
            }
        }
    }

    /// إرسال: نص فقط → محادثة صوتية؛ مع مرفقات → رفع ثم task.
    private func sendMessage(text: String) async {
        if pendingAttachments.isEmpty {
            if !text.isEmpty { await vm.routeVoiceTranscript(text) }
            return
        }
        let atts = pendingAttachments
        pendingAttachments = []
        var fileIDs: [String] = []
        if let um = enrollment.uploadManager {
            for att in atts {
                guard let data = att.data ?? (att.url.flatMap { try? Data(contentsOf: $0) }) else { continue }
                do {
                    let id = try await um.uploadAsync(data, filename: att.filename, mimeType: mime(for: att),
                                                      conversationID: conversationID(), sessionID: sessionID())
                    fileIDs.append(id)
                } catch { /* تخطي الملف الفاشل */ }
            }
        }
        if !text.isEmpty || !fileIDs.isEmpty {
            do {
                if let api = enrollment.api {
                    _ = try await api.post("/tasks", body: ["prompt": text, "attachment_ids": fileIDs])
                }
            } catch { /* log */ }
        }
    }

    private func mime(for att: PendingAttachment) -> String {
        switch att.kind {
        case "photo", "scan": return "image/jpeg"
        case "video": return "video/mp4"
        case "audio": return "audio/m4a"
        default: return "application/octet-stream"
        }
    }

    private func conversationID() -> String {
        let key = "jarvis.conversation.id"
        if let v = UserDefaults.standard.string(forKey: key) { return v }
        let v = UUID().uuidString
        UserDefaults.standard.set(v, forKey: key)
        return v
    }

    private func sessionID() -> String {
        let key = "jarvis.session.id"
        if let v = UserDefaults.standard.string(forKey: key) { return v }
        let v = UUID().uuidString
        UserDefaults.standard.set(v, forKey: key)
        return v
    }

}
