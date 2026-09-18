import SwiftUI

/// صندوق الوارد: الملفات القادمة (اسم/نوع/حجم/معاينة/مهمة/حالة).
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
                    Button("إعادة إرسال") { vm.resend(f) }.font(.caption)
                }
            }
            .navigationTitle("الوارد")
            .task { await vm.load() }
        }
    }
}

struct InboxFile: Identifiable {
    let id: String
    let filename: String
    let size: Int
    let status: String
    var icon: String { "doc" }
    var sizeDescription: String { ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file) }
}

@MainActor
final class InboxViewModel: ObservableObject {
    @Published var files: [InboxFile] = []
    func load() async { /* GET /files */ }
    func resend(_ f: InboxFile) { /* إعادة إرسال إلى جارفس */ }
}
