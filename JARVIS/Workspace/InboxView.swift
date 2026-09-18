import SwiftUI

/// صندوق الوارد: الملفات الواردة (اسم/نوع/حجم/حالة) مربوطة فعليًا بـ GET /files.
struct InboxView: View {
    @StateObject private var vm = InboxViewModel()

    var body: some View {
        NavigationView {
            List(vm.files) { f in
                HStack {
                    Image(systemName: f.icon).frame(width: 36)
                    VStack(alignment: .leading) {
                        Text(f.filename).font(.body).lineLimit(1)
                        Text("\(f.sizeDescription) · \(f.status)")
                            .font(.caption).foregroundColor(.secondary)
                    }
                    Spacer()
                    Button("إعادة إرسال") { Task { await vm.resend(f) } }.font(.caption)
                }
            }
            .navigationTitle("الوارد")
            .overlay { if vm.loading { ProgressView() } }
            .task { await vm.load() }
            .refreshable { await vm.load() }
        }
    }
}

struct InboxFile: Identifiable {
    let id: String
    let filename: String
    let size: Int
    let status: String
    var icon: String {
        switch status {
        case "image": return "photo"
        case "video": return "film"
        default: return "doc"
        }
    }
    var sizeDescription: String { ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file) }
}

@MainActor
final class InboxViewModel: ObservableObject {
    @Published var files: [InboxFile] = []
    @Published var loading = false

    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        loading = true
        defer { loading = false }
        do {
            let rows = try await api.get("/files")
            files = rows.compactMap { r in
                guard let id = r["file_id"] as? String else { return nil }
                return InboxFile(id: id,
                                 filename: r["filename"] as? String ?? id,
                                 size: r["size"] as? Int ?? 0,
                                 status: r["media_kind"] as? String ?? "file")
            }
        } catch { /* log */ }
    }

    func resend(_ f: InboxFile) async {
        // إعادة إرسال: إنشاء task بالمرفق
        var req = URLRequest(url: api.baseURL.appendingPathComponent("/tasks"))
        req.httpMethod = "POST"
        req.setValue(api.sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = ["prompt": "عالج الملف المرفق", "attachment_ids": [f.id]]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        _ = try? await URLSession.shared.data(for: req)
    }
}
