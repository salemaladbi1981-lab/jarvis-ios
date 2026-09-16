import Foundation

/// Launch latency instrumentation — يقيس launch → Home first frame → Core first frame → interactive.
/// لا يؤثر على الـ UI (print فقط في Xcode console).
enum LaunchTiming {
    static let bootUptime: TimeInterval = ProcessInfo.processInfo.systemUptime
    static func mark(_ label: String) {
        let elapsedMs = Int((ProcessInfo.processInfo.systemUptime - bootUptime) * 1000)
        print("[LAUNCH] \(label) @ \(elapsedMs)ms")
    }
}
