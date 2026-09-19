import SwiftUI

/// شريط معاينة المرفقات فوق الـ composer: thumbnail + اسم + X حذف.
struct AttachmentPreviewBar: View {
    let attachments: [PendingAttachment]
    let onRemove: (UUID) -> Void

    var body: some View {
        if attachments.isEmpty { return AnyView(EmptyView()) }
        return AnyView(
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(attachments) { att in
                        AttachmentThumb(att: att) { onRemove(att.id) }
                    }
                }
                .padding(.horizontal, JarvisSpacing.lg)
                .padding(.vertical, 6)
            }
        )
    }
}

struct AttachmentThumb: View {
    let att: PendingAttachment
    let onRemove: () -> Void

    var body: some View {
        VStack(spacing: 2) {
            ZStack(alignment: .topTrailing) {
                thumbnail
                    .frame(width: 64, height: 64)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(JarvisColor.primary_blue.opacity(0.25), lineWidth: 1))
                Button(action: onRemove) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 16))
                        .foregroundColor(.white)
                        .background(Circle().fill(.black.opacity(0.6)))
                }
                .offset(x: 5, y: -5)
            }
            Text(att.filename)
                .font(.system(size: 9))
                .foregroundColor(JarvisColor.text_muted)
                .lineLimit(1)
                .frame(width: 64)
        }
    }

    @ViewBuilder
    private var thumbnail: some View {
        #if os(iOS)
        if let data = att.data, let img = UIImage(data: data) {
            Image(uiImage: img).resizable().scaledToFill()
        } else {
            fallbackThumbnail
        }
        #else
        fallbackThumbnail
        #endif
    }

    private var fallbackThumbnail: some View {
        ZStack {
            JarvisColor.bg_1.opacity(0.6)
            Image(systemName: icon)
                .font(.system(size: 26))
                .foregroundColor(JarvisColor.text_muted)
        }
    }

    private var icon: String {
        switch att.kind {
        case "video": return "film"
        case "audio": return "waveform"
        case "scan": return "doc.viewfinder"
        default: return "doc"
        }
    }
}
