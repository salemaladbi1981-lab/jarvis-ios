import SwiftUI
import QuickLook

/// عرض مرفق سينمائي: صورة/فيديو/صوت عبر المشتق (thumbnail) + مستند عبر بطاقة،
/// مع حالات تحميل/فشل/إعادة محاولة صريحة (لا فشل صامت). الملكية server-side.
struct AttachmentView: View {
    let fileId: String
    let api: JarvisAPI

    @State private var file: FileItem?
    @State private var loadFailed = false
    @State private var previewURL: URL?

    var body: some View {
        Group {
            if let file = file {
                if file.isImage || file.isVideo || file.isAudio {
                    if file.hasThumbnail {
                        DerivativeThumb(fileId: fileId, api: api, kind: "thumbnail", badge: badgeIcon(file))
                    } else {
                        fileCard(file)
                    }
                } else {
                    fileCard(file)
                }
            } else if loadFailed {
                failedCard
            } else {
                loadingCard
            }
        }
        .task { await load() }
        .quickLookPreview($previewURL)
    }

    private var loadingCard: some View {
        HStack(spacing: 6) {
            ProgressView().scaleEffect(0.7)
            Text("تحميل المرفق…").font(.system(size: 12)).foregroundColor(JarvisColor.text_muted)
        }
        .padding(10)
        .background(JarvisColor.bg_1)
        .cornerRadius(10)
    }

    private var failedCard: some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle").foregroundColor(JarvisColor.danger)
            Text("تعذّر تحميل المرفق").font(.system(size: 12)).foregroundColor(JarvisColor.text_muted)
            Spacer()
            Button("إعادة المحاولة") { Task { await load() } }
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(JarvisColor.highlight_blue)
        }
        .padding(10)
        .background(JarvisColor.bg_1)
        .cornerRadius(10)
    }

    private func badgeIcon(_ f: FileItem) -> String {
        if f.isVideo { return "play.rectangle.fill" }
        if f.isAudio { return "waveform" }
        return "photo.fill"
    }

    private func fileCard(_ f: FileItem) -> some View {
        HStack(spacing: 10) {
            Image(systemName: f.isVideo ? "play.rectangle" : (f.isAudio ? "waveform" : (f.isDocument ? "doc.richtext" : "doc")))
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
            Button { Task { await open(f) } } label: {
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
        loadFailed = false
        do {
            file = try await api.getObject("files/\(fileId)")
        } catch {
            loadFailed = true
        }
    }

    private func open(_ f: FileItem) async {
        do {
            let (url, _) = try await api.download("files/\(fileId)/download")
            previewURL = url
        } catch {
            // تعذّر الفتح — يبقى على البطاقة
        }
    }
}

/// مصغّر مشتق (image thumbnail / video poster / audio waveform) — تحميل + فشل/إعادة.
struct DerivativeThumb: View {
    let fileId: String
    let api: JarvisAPI
    let kind: String
    let badge: String

    @State private var data: Data?
    @State private var failed = false

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            thumbBody
            Image(systemName: badge)
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(.white)
                .padding(6)
                .background(Color.black.opacity(0.55))
                .clipShape(Circle())
                .padding(6)
        }
        .frame(maxWidth: 260, maxHeight: 220)
        .task { await load() }
        .animation(.easeIn(duration: 0.22), value: data != nil)
    }

    @ViewBuilder
    private var thumbBody: some View {
        #if os(iOS)
        if let data = data, let ui = UIImage(data: data) {
            Image(uiImage: ui)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: 260, maxHeight: 220)
                .cornerRadius(10)
                .shadow(color: .black.opacity(0.25), radius: 8, y: 4)
        } else if failed {
            VStack(spacing: 6) {
                Image(systemName: "photo.badge.exclamationmark")
                    .font(.system(size: 20))
                    .foregroundColor(JarvisColor.text_muted)
                Button("إعادة المحاولة") { Task { await load() } }
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(JarvisColor.highlight_blue)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(12)
        } else {
            ProgressView().padding(12)
        }
        #elseif os(macOS)
        if let data = data, let ns = NSImage(data: data) {
            Image(nsImage: ns)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: 260, maxHeight: 220)
                .cornerRadius(10)
                .shadow(color: .black.opacity(0.25), radius: 8, y: 4)
        } else if failed {
            VStack(spacing: 6) {
                Image(systemName: "photo.badge.exclamationmark").foregroundColor(JarvisColor.text_muted)
                Button("إعادة المحاولة") { Task { await load() } }.font(.caption).foregroundColor(JarvisColor.highlight_blue)
            }.padding(12)
        } else {
            ProgressView().padding(12)
        }
        #else
        ProgressView().padding(12)
        #endif
    }

    private func load() async {
        failed = false
        do {
            data = try await api.fetchData("files/\(fileId)/derivative/\(kind)")
        } catch {
            failed = true
        }
    }
}
