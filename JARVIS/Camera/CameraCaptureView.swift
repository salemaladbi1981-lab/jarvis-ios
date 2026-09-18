import SwiftUI
import AVFoundation

/// كاميرا صورة (AVFoundation): زر X للإغلاق، معاينة Use/Retake، لا رفع قبل الموافقة.
struct CameraCaptureView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var model = CameraModel()
    let onUsePhoto: (Data, String) -> Void

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            if let img = model.capturedImage {
                Image(uiImage: img).resizable().scaledToFit().ignoresSafeArea()
                VStack {
                    closeButton
                    Spacer()
                    HStack(spacing: 24) {
                        Button("إعادة التصوير") { model.retake() }
                            .padding(.horizontal).padding(.vertical, 10)
                            .background(.red.opacity(0.85)).foregroundColor(.white).cornerRadius(10)
                        Button("استخدام الصورة") {
                            if let d = model.capturedData {
                                onUsePhoto(d, "image/jpeg")
                                dismiss()
                            }
                        }
                        .padding(.horizontal).padding(.vertical, 10)
                        .background(.green).foregroundColor(.white).cornerRadius(10)
                    }.padding(.bottom, 30)
                }
            } else {
                CameraPreviewLayer(session: model.session).ignoresSafeArea()
                VStack {
                    HStack {
                        closeButton
                        Spacer()
                        Button(action: model.toggleCamera) {
                            Image(systemName: "arrow.triangle.2.circlepath.camera").font(.title).foregroundColor(.white)
                        }.padding()
                        Button(action: model.toggleFlash) {
                            Image(systemName: model.isFlashOn ? "bolt.fill" : "bolt.slash").font(.title)
                                .foregroundColor(model.isFlashOn ? .yellow : .white)
                        }.padding()
                    }
                    Spacer()
                    Button(action: model.capture) {
                        Circle().strokeBorder(.white, lineWidth: 3).frame(width: 74, height: 74)
                            .overlay(Circle().fill(.white).frame(width: 60, height: 60))
                    }.padding(.bottom, 30)
                }
            }
        }
        .onAppear { model.requestAndStart() }
        .onDisappear { model.stop() }
    }

    private var closeButton: some View {
        HStack {
            Button(action: { dismiss() }) {
                Image(systemName: "xmark.circle.fill").font(.title).foregroundColor(.white)
                    .shadow(radius: 3)
            }
            Spacer()
        }.padding()
    }
}

@MainActor
final class CameraModel: NSObject, ObservableObject {
    @Published var isFlashOn = false
    @Published var capturedImage: UIImage?
    @Published var capturedData: Data?
    @Published var permissionDenied = false

    let session = AVCaptureSession()
    private var videoInput: AVCaptureDeviceInput?
    private let photoOutput = AVCapturePhotoOutput()
    private var usingFront = false
    private var cameraDelegate: PhotoDelegate?

    func requestAndStart() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: configure()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { granted in
                Task { @MainActor in
                    granted ? self.configure() : (self.permissionDenied = true)
                }
            }
        default: permissionDenied = true
        }
    }

    private func device() -> AVCaptureDevice? {
        AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: usingFront ? .front : .back)
    }

    func configure() {
        session.beginConfiguration()
        if let old = videoInput { session.removeInput(old); videoInput = nil }
        if let d = device(), let input = try? AVCaptureDeviceInput(device: d), session.canAddInput(input) {
            session.addInput(input); videoInput = input
        }
        if session.canAddOutput(photoOutput) && !session.outputs.contains(where: { $0 === photoOutput }) {
            session.addOutput(photoOutput)
        }
        session.commitConfiguration()
        if !session.isRunning { session.startRunning() }
    }

    func stop() { if session.isRunning { session.stopRunning() } }
    func toggleCamera() { usingFront.toggle(); configure() }
    func toggleFlash() { isFlashOn.toggle() }

    func capture() {
        let settings = AVCapturePhotoSettings()
        settings.flashMode = isFlashOn ? .on : .off
        let delegate = PhotoDelegate { [weak self] data in
            Task { @MainActor in
                self?.capturedData = data
                self?.capturedImage = UIImage(data: data)
            }
        }
        cameraDelegate = delegate
        photoOutput.capturePhoto(with: settings, delegate: delegate)
    }
    func retake() { capturedImage = nil; capturedData = nil }
}

final class PhotoDelegate: NSObject, AVCapturePhotoCaptureDelegate {
    private let onPhoto: (Data) -> Void
    init(_ onPhoto: @escaping (Data) -> Void) { self.onPhoto = onPhoto }
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        if let d = photo.fileDataRepresentation() { onPhoto(d) }
    }
}

struct CameraPreviewLayer: UIViewRepresentable {
    let session: AVCaptureSession
    func makeUIView(context: Context) -> UIView {
        let v = UIView()
        let layer = AVCaptureVideoPreviewLayer(session: session)
        layer.videoGravity = .resizeAspectFill
        layer.frame = UIScreen.main.bounds
        v.layer.addSublayer(layer)
        return v
    }
    func updateUIView(_ v: UIView, context: Context) {
        (v.layer.sublayers?.first as? AVCaptureVideoPreviewLayer)?.session = session
    }
}
