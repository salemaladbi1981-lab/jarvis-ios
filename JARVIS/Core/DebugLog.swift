import Foundation

/// سجل تشخيص يُكتب إلى Documents/jarvis-voice.log (يُسحب عبر ios-deploy --download).
/// آخر سطر قبل التعطّل يحدد أين مات المسار الصوتي.
enum DebugLog {
    static let url: URL = {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return dir.appendingPathComponent("jarvis-voice.log")
    }()

    static func write(_ s: String) {
        let line = "\(String(format: "%.3f", Date().timeIntervalSince1970)) \(s)\n"
        guard let data = line.data(using: .utf8) else { return }
        if let fh = try? FileHandle(forWritingTo: url) {
            defer { try? fh.close() }
            _ = try? fh.seekToEnd()
            try? fh.write(contentsOf: data)
        } else {
            try? data.write(to: url)
        }
    }
}
