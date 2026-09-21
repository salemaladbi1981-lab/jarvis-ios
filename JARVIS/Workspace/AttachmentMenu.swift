import SwiftUI
import PhotosUI

/// قائمة مرفقات: صورة، فيديو، ملفات، كاميرا، مسح، صوت، متعدد.
struct AttachmentMenu: View {
    let onPickPhotos: () -> Void
    let onPickVideos: () -> Void
    let onPickFiles: () -> Void
    let onCameraPhoto: () -> Void
    let onCameraVideo: () -> Void
    let onScanDocument: () -> Void
    let onRecordAudio: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("إضافة مرفق")
                .font(.headline)
                .foregroundColor(JarvisColor.text_primary)
            HStack {
                attachItem("photo", "صورة", onPickPhotos)
                attachItem("video", "فيديو", onPickVideos)
                attachItem("folder", "ملفات", onPickFiles)
            }
            HStack {
                attachItem("camera", "كاميرا", onCameraPhoto)
                attachItem("video.camera", "تصوير", onCameraVideo)
                attachItem("doc.viewfinder", "مسح", onScanDocument)
                attachItem("mic", "صوت", onRecordAudio)
            }
        }
        .padding()
    }

    private func attachItem(_ icon: String, _ label: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundColor(JarvisColor.primary_gold)
                Text(label)
                    .font(.caption)
                    .foregroundColor(JarvisColor.text_secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(JarvisColor.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(JarvisColor.primary_gold.opacity(0.18), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}
