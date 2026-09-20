import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

/// الشاشة الرئيسية (Concept 2) — نواة سينمائية + زر مايك بارز + محادثات/مهام/تسليمات + شريط إدخال سفلي.
/// تبقى الجذر الإنتاجي للواجهة (RootView.tabs → HomeEntryView)، ولا نرجع إلى HomeView القديم.
struct HomeEntryView: View {
    @StateObject private var vm: HomeEntryViewModel
    @StateObject private var voiceVM = HomeViewModel()
    @EnvironmentObject private var enrollment: EnrollmentManager
    @State private var newConv: ConvID?
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
    @State private var sendError: String?
    @State private var retryText = ""
    @State private var isSending = false
    @Environment(\.scenePhase) private var scenePhase
    private let api: JarvisAPI

    init(api: JarvisAPI) {
        self.api = api
        _vm = StateObject(wrappedValue: HomeEntryViewModel(api: api))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Concept 2: النواة السينمائية + زر المايك البارز (مرتبطان بحالة/مستوى الصوت الحقيقي)
                    JarvisHeroView(vm: voiceVM)
                    JarvisMicControl(vm: voiceVM)

                    // نتيجة أدوات التقويم/التذكيرات (تُعرض هنا بدل الرد الصوتي الثاني — دماغ واحد)
                    if let msg = voiceVM.calendarMessage {
                        Text(msg)
                            .font(.system(size: 14))
                            .foregroundColor(JarvisColor.text_primary)
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(RoundedRectangle(cornerRadius: 12).fill(JarvisColor.bg_1.opacity(0.45)))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(JarvisColor.primary_blue.opacity(0.16), lineWidth: 1))
                    }

                    // نقطة دخول واضحة لبدء محادثة جديدة
                    Button {
                        Task {
                            if let c = await vm.newConversation() {
                                newConv = ConvID(id: c.id)
                            }
                        }
                    } label: {
                        HStack(spacing: 10) {
                            Image(systemName: "plus.bubble.fill")
                            Text("بدء محادثة جديدة")
                                .font(.system(size: 16, weight: .semibold))
                        }
                        .foregroundColor(JarvisColor.text_primary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(JarvisColor.bg_1)
                        .cornerRadius(14)
                    }

                    if let nce = vm.newConversationError {
                        Text(nce)
                            .font(.system(size: 13))
                            .foregroundColor(JarvisColor.danger)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    if !vm.conversations.isEmpty {
                        section("المحادثات الأخيرة") {
                            ForEach(vm.conversations.prefix(5)) { c in
                                NavigationLink {
                                    ConversationView(api: api, conversationId: c.id)
                                } label: {
                                    row(icon: "bubble.left", title: c.title ?? "محادثة",
                                        subtitle: c.source)
                                }
                            }
                        }
                    }

                    if !vm.activeTasks.isEmpty {
                        section("المهام الجارية") {
                            ForEach(vm.activeTasks.prefix(3)) { t in
                                NavigationLink {
                                    TaskDetailView(api: api, taskId: t.id)
                                } label: {
                                    row(icon: "hammer", title: t.prompt ?? "مهمة",
                                        subtitle: "قيد التنفيذ")
                                }
                            }
                        }
                    }

                    if !vm.deliveries.isEmpty {
                        section("التسليمات الأخيرة") {
                            ForEach(vm.deliveries.prefix(3)) { d in
                                NavigationLink {
                                    DeliveryDetailView(api: api, deliveryId: d.id)
                                } label: {
                                    row(icon: "doc", title: d.filename ?? "تسليم",
                                        subtitle: d.type)
                                }
                            }
                        }
                    }

                    if vm.conversations.isEmpty && vm.activeTasks.isEmpty && vm.deliveries.isEmpty {
                        VStack(spacing: 8) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 30))
                                .foregroundColor(JarvisColor.text_muted)
                            Text("ابدأ محادثة مع جارفس")
                                .foregroundColor(JarvisColor.text_muted)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 24)
                    }
                }
                .padding(16)
            }
            .navigationTitle("جارفس")
            .navigationDestination(item: $newConv) { c in
                ConversationView(api: api, conversationId: c.id, initialText: c.initialText)
            }
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 0) {
                AttachmentPreviewBar(attachments: pendingAttachments) { id in
                    pendingAttachments.removeAll { $0.id == id }
                }
                if let err = sendError {
                    HStack {
                        Text(err).font(.caption).foregroundColor(.red)
                        Spacer()
                        Button("إعادة المحاولة") {
                            let t = retryText
                            sendError = nil
                            Task { await sendMessage(text: t) }
                        }
                        .font(.caption).foregroundColor(.blue)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 6)
                }
                WorkspaceComposerView(
                    text: $composerText,
                    hasAttachments: !pendingAttachments.isEmpty,
                    onSend: {
                        let t = composerText.trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !t.isEmpty || !pendingAttachments.isEmpty else { return }
                        composerText = ""
                        Task { await sendMessage(text: t) }
                    },
                    onAttach: { showAttachments = true },
                    onMic: { voiceVM.toggleVoice() }
                )
                .padding(.horizontal, 16)
            }
            .background(JarvisColor.bg_0.opacity(0.92))
        }
        .background(
            LinearGradient(colors: [JarvisColor.bg_0, JarvisColor.bg_1], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
        )
        .overlay(alignment: .top) {
            if ProcessInfo.processInfo.arguments.contains("-diagnostics") {
                diagnosticsPanel
            }
        }
        .task {
            await vm.load()
            await voiceVM.load()
            voiceVM.handleAppIntentStart()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { voiceVM.handleAppBackgrounded() }
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
        #if os(iOS)
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
        #endif
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
        #if os(iOS)
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
        #endif
    }

    private func section(_ title: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(JarvisColor.text_muted)
            VStack(spacing: 0) { content() }
        }
    }

    private func row(icon: String, title: String, subtitle: String?) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 15))
                .foregroundColor(JarvisColor.highlight_blue)
                .frame(width: 22)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 15))
                    .foregroundColor(JarvisColor.text_primary)
                    .lineLimit(1)
                if let s = subtitle, !s.isEmpty {
                    Text(s)
                        .font(.system(size: 12))
                        .foregroundColor(JarvisColor.text_muted)
                }
            }
            Spacer()
            Image(systemName: "chevron.left")
                .font(.system(size: 12))
                .foregroundColor(JarvisColor.text_muted)
        }
        .padding(.vertical, 10)
    }

    /// تشخيص مُمنهج على الشاشة (عبر -diagnostics) — يظهر حالة المصادقة/الـAPI/التنقل بدون Xcode console.
    private var diagnosticsPanel: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text("JARVIS DIAG").font(.caption2).bold().foregroundColor(.white)
            Text("enrolled: \(enrollment.isEnrolled)")
            Text("sessionToken: \(enrollment.sessionToken != nil ? "present" : "nil")")
            Text("api: \(enrollment.api != nil ? "present" : "nil")")
            Text("uploadManager: \(enrollment.uploadManager != nil ? "present" : "nil")")
            Text("newConv: \(newConv?.id ?? "nil")")
            Text("sendError: \(sendError ?? "none")")
            Text("newConversationError: \(vm.newConversationError ?? "none")")
        }
        .font(.caption2.monospaced())
        .foregroundColor(.white)
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.black.opacity(0.78))
        .cornerRadius(8)
        .padding(8)
        .allowsHitTesting(false)
    }

    /// إرسال: نص فقط → توجيه نص؛ مع مرفقات → رفع ثم task. لا تُمسح المرفقات إلا بعد النجاح.
    private func sendMessage(text: String) async {
        guard !isSending else { return }
        isSending = true
        defer { isSending = false }
        retryText = text
        if pendingAttachments.isEmpty {
            if !text.isEmpty {
                // مسار الدردشة النصية الحقيقي — إنشاء محادثة ثم الانتقال لشاشة الدردشة (وليس routeVoiceTranscript)
                if let c = await vm.newConversation() {
                    newConv = ConvID(id: c.id, initialText: text)
                }
            }
            return
        }
        let atts = pendingAttachments
        var fileIDs: [String] = []

        guard let um = enrollment.uploadManager else {
            sendError = "الرفع غير متاح — أعد المحاولة"
            return
        }
        for att in atts {
            guard let data = att.data ?? (att.url.flatMap { try? Data(contentsOf: $0) }) else {
                sendError = "تعذّر قراءة المرفق — أعد المحاولة"
                return
            }
            do {
                let id = try await um.uploadAsync(data, filename: att.filename, mimeType: mime(for: att),
                                                  conversationID: conversationID(), sessionID: sessionID())
                fileIDs.append(id)
            } catch {
                sendError = "فشل رفع المرفق: \(error.localizedDescription)"
                return
            }
        }
        do {
            _ = try await api.post("/tasks", body: ["prompt": text, "attachment_ids": fileIDs])
        } catch {
            sendError = "فشل إنشاء المهمة — أعد المحاولة"
            return
        }
        pendingAttachments = []
        sendError = nil
        retryText = ""
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

@MainActor
final class HomeEntryViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var activeTasks: [JarvisTask] = []
    @Published var deliveries: [DeliveryItem] = []
    @Published var newConversationId: String?
    @Published var newConversationError: String?
    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        async let convs: [Conversation] = api.getArray("conversations")
        async let tasks: [JarvisTask] = api.getArray("tasks")
        async let dels: [DeliveryItem] = api.getArray("deliveries")
        do {
            let (c, t, d) = try await (convs, tasks, dels)
            conversations = c
            activeTasks = t.filter { ["QUEUED", "RUNNING"].contains(($0.jobState ?? $0.status ?? "").uppercased()) }
            deliveries = d
        } catch {
            conversations = []; activeTasks = []; deliveries = []
        }
    }

    /// إنشاء محادثة حقيقية عبر الـ backend — لا تبتلع الخطأ.
    @discardableResult
    func newConversation() async -> Conversation? {
        do {
            let env: ConversationEnvelope = try await api.postObject("conversations", body: [:])
            let c = env.conversation
            newConversationId = c.id
            newConversationError = nil
            return c
        } catch {
            let msg = "تعذّر بدء محادثة جديدة: \(error.localizedDescription)"
            newConversationError = msg
            print("[JARVIS-HOME] newConversation failed: \(error)")
            return nil
        }
    }
}

struct ConvID: Identifiable, Hashable {
    let id: String
    let initialText: String?
    init(id: String, initialText: String? = nil) { self.id = id; self.initialText = initialText }
}
