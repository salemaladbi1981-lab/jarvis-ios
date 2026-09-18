import SwiftUI
import AVFoundation

/// تسجيل صوتي بسيط (AVAudioRecorder) → m4a.
struct AudioRecorderView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var recorder = AudioRecorderModel()
    let onRecorded: (URL) -> Void

    var body: some View {
        VStack {
            HStack {
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill").font(.title)
                }
                Spacer()
            }.padding()
            Spacer()
            if let url = recorder.recordedURL {
                Text("تم التسجيل").font(.title2)
                HStack(spacing: 24) {
                    Button("إعادة") { recorder.reset() }
                        .padding().background(.red.opacity(0.85)).foregroundColor(.white).cornerRadius(10)
                    Button("استخدام") { onRecorded(url); dismiss() }
                        .padding().background(.green).foregroundColor(.white).cornerRadius(10)
                }
            } else {
                Button(action: recorder.toggle) {
                    Circle().fill(recorder.isRecording ? .red : .blue).frame(width: 74, height: 74)
                }
                Text(recorder.isRecording ? "اضغط للإيقاف" : "اضغط للتسجيل").foregroundColor(.secondary)
            }
            Spacer()
        }
        .environment(\.layoutDirection, .rightToLeft)
        .preferredColorScheme(.dark)
    }
}

@MainActor
final class AudioRecorderModel: NSObject, ObservableObject, AVAudioRecorderDelegate {
    @Published var isRecording = false
    @Published var recordedURL: URL?
    private var recorder: AVAudioRecorder?

    func toggle() { isRecording ? stop() : start() }
    func start() {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("audio-\(UUID().uuidString).m4a")
        let settings: [String: Any] = [AVFormatIDKey: kAudioFormatMPEG4AAC, AVSampleRateKey: 44100, AVNumberOfChannelsKey: 1]
        recorder = try? AVAudioRecorder(url: url, settings: settings)
        recorder?.delegate = self
        recorder?.record()
        isRecording = true
    }
    func stop() { recorder?.stop(); isRecording = false; recordedURL = recorder?.url }
    func reset() { recordedURL = nil }
}
