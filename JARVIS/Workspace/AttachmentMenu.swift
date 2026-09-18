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
            Text("إضافة مرفق").font(.headline)
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
            VStack {
                Image(systemName: icon).font(.title2)
                Text(label).font(.caption)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(Color(.secondarySystemBackground))
            .cornerRadius(10)
        }
    }
}
