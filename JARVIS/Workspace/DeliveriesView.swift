import SwiftUI

/// مركز التسليمات: مخرجات جارفس (فيديو/صور/PDF/…) مع فتح/مشاركة/حفظ/نسخة جديدة.
struct DeliveriesView: View {
    @StateObject private var vm = DeliveriesViewModel()

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
                    Button("فتح") { vm.open(d) }.font(.caption)
                }
            }
            .navigationTitle("التسليمات")
            .task { await vm.load() }
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
        case "markdown", "script", "prompt", "caption", "code", "json": return "doc.text"
        default: return "doc"
        }
    }
}

@MainActor
final class DeliveriesViewModel: ObservableObject {
    @Published var items: [Delivery] = []
    func load() async { /* GET /deliveries */ }
    func open(_ d: Delivery) { /* فتح/تنزيل */ }
}
