import SwiftUI
import AVFoundation
import AVKit  // لـ AVPlayerViewController

/// كاميرا فيديو حقيقية (AVCaptureMovieFileOutput): start/stop، أمامي/خلفي، ميكروفون، torch، preview، retake، use.
struct CameraVideoView: View {
    @StateObject private var model = CameraVideoModel()
    let onUseVideo: (URL) -> Void

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            if let url = model.recordedURL {
                VideoPlayerLayer(url: url).ignoresSafeArea()
                VStack {
                    Spacer()
                    HStack {
                        Button("إعادة التصوير") { model.retake() }
                            .padding().background(.red.opacity(0.8)).foregroundColor(.white).cornerRadius(10)
                        Button("استخدام الفيديو") { onUseVideo(url) }
                            .padding().background(.green).foregroundColor(.white).cornerRadius(10)
                    }.padding(.bottom, 30)
                }
            } else {
                CameraPreviewLayer(session: model.session).ignoresSafeArea()
                VStack {
                    HStack {
                        Button(action: model.toggleCamera) {
                            Image(systemName: "arrow.triangle.2.circlepath.camera").font(.title).foregroundColor(.white)
                        }.padding()
                        Spacer()
                        Button(action: model.toggleTorch) {
                            Image(systemName: model.isTorchOn ? "bolt.fill" : "bolt.slash").font(.title)
                                .foregroundColor(model.isTorchOn ? .yellow : .white)
                        }.padding()
                    }
                    Spacer()
                    Button(action: model.isRecording ? model.stopRecording : model.startRecording) {
                        Circle().fill(model.isRecording ? .red : .white).frame(width: 74, height: 74)
                    }.padding(.bottom, 30)
                }
            }
        }
        .onAppear { model.requestAndStart() }
        .onDisappear { model.stop() }
    }
}

@MainActor
final class CameraVideoModel: NSObject, ObservableObject, AVCaptureFileOutputRecordingDelegate {
    @Published var isRecording = false
    @Published var isTorchOn = false
    @Published var recordedURL: URL?
    @Published var permissionDenied = false

    let session = AVCaptureSession()
    private var videoInput: AVCaptureDeviceInput?
    private var audioInput: AVCaptureDeviceInput?
    private let movieOutput = AVCaptureMovieFileOutput()
    private var usingFront = false

    func requestAndStart() {
        AVCaptureDevice.requestAccess(for: .video) { _ in
            AVCaptureDevice.requestAccess(for: .audio) { _ in
                Task { @MainActor in self.configure() }
            }
        }
    }

    private func device() -> AVCaptureDevice? {
        AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: usingFront ? .front : .back)
    }

    func configure() {
        session.beginConfiguration()
        session.sessionPreset = .high
        if let old = videoInput { session.removeInput(old); videoInput = nil }
        if let d = device(), let input = try? AVCaptureDeviceInput(device: d), session.canAddInput(input) {
            session.addInput(input); videoInput = input
        }
        // ميكروفون
        if let mic = AVCaptureDevice.default(for: .audio),
           let a = try? AVCaptureDeviceInput(device: mic), session.canAddInput(a) {
            session.addInput(a); audioInput = a
        }
        if session.canAddOutput(movieOutput) && !session.outputs.contains(where: { $0 === movieOutput }) {
            session.addOutput(movieOutput)
        }
        session.commitConfiguration()
        if !session.isRunning { session.startRunning() }
    }

    func stop() { if session.isRunning { session.stopRunning() } }
    func toggleCamera() { usingFront.toggle(); configure() }
    func toggleTorch() {
        guard let d = device(), d.hasTorch else { return }
        try? d.lockForConfiguration()
        d.torchMode = isTorchOn ? .off : .on
        d.unlockForConfiguration()
        isTorchOn.toggle()
    }

    func startRecording() {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("video-\(UUID().uuidString).mov")
        movieOutput.startRecording(to: url, recordingDelegate: self)
        isRecording = true
    }
    func stopRecording() {
        movieOutput.stopRecording()
        isRecording = false
    }
    func retake() { recordedURL = nil }

    nonisolated func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        Task { @MainActor in
            if error == nil { self.recordedURL = outputFileURL }
        }
    }
}

struct VideoPlayerLayer: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let vc = AVPlayerViewController()
        vc.player = AVPlayer(url: url)
        vc.player?.play()
        return vc
    }
    func updateUIViewController(_ vc: AVPlayerViewController, context: Context) {}
}
