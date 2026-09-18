import SwiftUI
import AVFoundation

/// كاميرا حقيقية (AVFoundation): أمامي/خلفي، فلاش، معاينة، إعادة تصوير.
/// ليست PhotosPicker — التقاط مباشر من الكاميرا.
struct CameraCaptureView: View {
    @StateObject private var model = CameraModel()
    let onCapture: (Data, String) -> Void  // (data, mimeType)

    var body: some View {
        ZStack {
            CameraPreview(session: model.session).ignoresSafeArea()
            VStack {
                HStack {
                    Button(action: model.toggleCamera) {
                        Image(systemName: "arrow.triangle.2.circlepath.camera").font(.title).foregroundColor(.white)
                    }
                    Spacer()
                    Button(action: model.toggleFlash) {
                        Image(systemName: model.isFlashOn ? "bolt.fill" : "bolt.slash").font(.title)
                            .foregroundColor(model.isFlashOn ? .yellow : .white)
                    }
                }.padding()
                Spacer()
                Button(action: { model.capture(onCapture) }) {
                    Circle().strokeBorder(.white, lineWidth: 3).frame(width: 74, height: 74)
                        .overlay(Circle().fill(.white).frame(width: 60, height: 60))
                }
                Button("إعادة التصوير") { model.retake() }.foregroundColor(.white).padding(.top, 8)
            }
        }
        .onAppear { model.start() }
        .onDisappear { model.stop() }
    }
}

final class CameraModel: NSObject, ObservableObject {
    @Published var isFlashOn = false
    @Published var captured: Data?
    let session = AVCaptureSession()
    private var input: AVCaptureDeviceInput?
    private let output = AVCapturePhotoOutput()
    private var usingFront = false
    private var previewLayer: AVCaptureVideoPreviewLayer?

    func start() {
        session.sessionPreset = .high
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: usingFront ? .front : .back) else { return }
        do {
            input = try AVCaptureDeviceInput(device: device)
            if let i = input, session.canAddInput(i) { session.addInput(i) }
            if session.canAddOutput(output) { session.addOutput(output) }
            session.startRunning()
        } catch { /* handle */ }
    }
    func stop() { session.stopRunning() }
    func toggleCamera() { usingFront.toggle(); stop(); start() }
    func toggleFlash() { isFlashOn.toggle() }
    func capture(_ onCapture: @escaping (Data, String) -> Void) {
        let settings = AVCapturePhotoSettings()
        settings.flashMode = isFlashOn ? .on : .off
        output.capturePhoto(with: settings, delegate: Self.delegate(onCapture))
    }
    func retake() { captured = nil }
    private static func delegate(_ onCapture: @escaping (Data, String) -> Void) -> NSObject & AVCapturePhotoCaptureDelegate {
        final class D: NSObject, AVCapturePhotoCaptureDelegate {
            let cb: (Data, String) -> Void
            init(_ cb: @escaping (Data, String) -> Void) { self.cb = cb }
            func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
                if let d = photo.fileDataRepresentation() { cb(d, "image/jpeg") }
            }
        }
        return D(onCapture)
    }
}

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    func makeUIView(context: Context) -> UIView {
        let v = UIView()
        let layer = AVCaptureVideoPreviewLayer(session: session)
        layer.videoGravity = .resizeAspectFill
        v.layer.addSublayer(layer)
        return v
    }
    func updateUIView(_ uiView: UIView, context: Context) {}
}
