import SwiftUI
import QuickLook

/// عرض مرفق حقيقي: صورة داخل المحادثة، أو بطاقة ملف (PDF/عام) قابلة للفتح.
/// الملكية تُفرض server-side عبر GET /files/{id} (session token).
struct AttachmentView: View {
    let fileId: String
    let api: JarvisAPI

    @State private var file: FileItem?
    @State private var imageData: Data?
    @State private var previewURL: URL?

    var body: some View {
        Group {
            if let file = file {
                if file.isImage {
                    imageBody
                } else {
                    fileCard(file)
                }
            } else {
                HStack(spacing: 6) {
                    ProgressView().scaleEffect(0.7)
                    Text("مرفق…").font(.system(size: 12)).foregroundColor(JarvisColor.text_muted)
                }
                .padding(8)
                .background(JarvisColor.bg_1)
                .cornerRadius(8)
            }
        }
        .task { await load() }
        .quickLookPreview($previewURL)
    }

    @ViewBuilder
    private var imageBody: some View {
        if let data = imageData, let ui = UIImage(data: data) {
            Image(uiImage: ui)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: 260, maxHeight: 220)
                .cornerRadius(10)
        } else {
            ProgressView().padding(12)
        }
    }

    private func fileCard(_ f: FileItem) -> some View {
        HStack(spacing: 10) {
            Image(systemName: f.isDocument ? "doc.richtext" : "doc")
                .font(.system(size: 18))
                .foregroundColor(JarvisColor.highlight_blue)
            VStack(alignment: .leading, spacing: 2) {
                Text(f.filename ?? "ملف")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(JarvisColor.text_primary)
                    .lineLimit(1)
                Text("\(f.mimeType ?? "ملف") · \(sizeLabel(f.size))")
                    .font(.system(size: 11))
                    .foregroundColor(JarvisColor.text_muted)
            }
            Spacer()
            Button {
                Task { await open(f) }
            } label: {
                Image(systemName: "arrow.down.circle")
                    .font(.system(size: 20))
                    .foregroundColor(JarvisColor.highlight_blue)
            }
        }
        .padding(10)
        .background(JarvisColor.bg_1)
        .cornerRadius(10)
    }

    private func sizeLabel(_ s: Int?) -> String {
        guard let s = s else { return "" }
        if s >= 1_048_576 { return String(format: "%.1f MB", Double(s) / 1_048_576) }
        if s >= 1024 { return String(format: "%.1f KB", Double(s) / 1024) }
        return "\(s) B"
    }

    private func load() async {
        do {
            file = try await api.getObject("files/\(fileId)")
            if file?.isImage == true {
                imageData = try await api.fetchData("files/\(fileId)/download")
            }
        } catch {
            file = FileItem(fileId: fileId, filename: "مرفق غير متاح", mimeType: nil, size: nil, mediaKind: "file", status: "unavailable")
        }
    }

    private func open(_ f: FileItem) async {
        do {
            let (url, _) = try await api.download("files/\(fileId)/download")
            previewURL = url
        } catch {
            // تجاهل — يعرض فقط
        }
    }
}
