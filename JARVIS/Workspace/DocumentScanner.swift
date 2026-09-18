import SwiftUI
import VisionKit

/// مسح مستند حقيقي (VisionKit) → صور صفحات.
struct DocumentScanner: UIViewControllerRepresentable {
    var onScan: ([URL]) -> Void

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let vc = VNDocumentCameraViewController()
        vc.delegate = context.coordinator
        return vc
    }
    func updateUIViewController(_ vc: VNDocumentCameraViewController, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator(onScan: onScan) }

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let onScan: ([URL]) -> Void
        init(onScan: @escaping ([URL]) -> Void) { self.onScan = onScan }
        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFinishWith scan: VNDocumentCameraScan) {
            var urls: [URL] = []
            for i in 0..<scan.pageCount {
                if let data = scan.imageOfPage(at: i).jpegData(compressionQuality: 0.9) {
                    let url = FileManager.default.temporaryDirectory.appendingPathComponent("scan-\(i)-\(UUID().uuidString).jpg")
                    try? data.write(to: url)
                    urls.append(url)
                }
            }
            controller.dismiss(animated: true)
            onScan(urls)
        }
        func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) { controller.dismiss(animated: true) }
        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFailWithError error: Error) { controller.dismiss(animated: true) }
    }
}
