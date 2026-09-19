import SwiftUI

/// مركز التسليمات: مخرجات جارفس مربوطة فعليًا بـ GET /deliveries + فتح/تنزيل/مشاركة.
struct DeliveriesView: View {
    @StateObject private var vm: DeliveriesViewModel

    init(api: JarvisAPI) {
        _vm = StateObject(wrappedValue: DeliveriesViewModel(api: api))
    }

    var body: some View {
        NavigationView {
            List(vm.items) { d in
                HStack {
                    Image(systemName: d.icon).frame(width: 36)
                    VStack(alignment: .leading) {
                        Text(d.filename).font(.body).lineLimit(1)
                        Text(d.type).font(.caption).foregroundColor(.secondary)
                    }
                    Spacer()
                    Button("فتح") { Task { await vm.open(d) } }.font(.caption)
                }
            }
            .navigationTitle("التسليمات")
            .overlay { if vm.loading { ProgressView() } }
            .task { await vm.load() }
            .refreshable { await vm.load() }
        }
    }
}

struct Delivery: Identifiable {
    let id: String
    let filename: String
    let type: String
    var icon: String {
        switch type {
        case "video": return "film"
        case "image", "image_set": return "photo"
        case "pdf", "docx": return "doc.text"
        case "pptx": return "rectangle.on.rectangle"
        case "xlsx": return "tablecells"
        case "zip": return "archivebox"
        case "audio": return "waveform"
        default: return "doc.text"
        }
    }
}

@MainActor
final class DeliveriesViewModel: ObservableObject {
    @Published var items: [Delivery] = []
    @Published var loading = false

    private let api: JarvisAPI
    init(api: JarvisAPI) { self.api = api }

    func load() async {
        loading = true
        defer { loading = false }
        do {
            let rows = try await api.get("/deliveries")
            items = rows.compactMap { r in
                guard let id = r["delivery_id"] as? String else { return nil }
                return Delivery(id: id,
                                filename: r["filename"] as? String ?? id,
                                type: r["type"] as? String ?? "file")
            }
        } catch { /* log */ }
    }

    func open(_ d: Delivery) async {
        do {
            let (tmp, name) = try await api.download("/deliveries/\(d.id)/download")
            // فتح/مشاركة عبر ActivityViewController (iOS فقط)
            #if os(iOS)
            await MainActor.run {
                let vc = UIActivityViewController(activityItems: [tmp], applicationActivities: nil)
                UIApplication.shared.connectedScenes.compactMap { ($0 as? UIWindowScene)?.keyWindow }
                    .first?.rootViewController?.present(vc, animated: true)
            }
            #endif
        } catch { /* log */ }
    }
}
