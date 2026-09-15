import Foundation

/// Internal, safe preflight diagnostics. No secrets, no personal data.
struct PreflightReport {
    let appVersion: String
    let appBuild: String
    let backendReachable: String   // reachable | unreachable | not_configured
    let realtimeAvailable: String  // available | unavailable (no credential)
    let micPermission: String
    let calendarPermission: String
    let remindersPermission: String
    let providerMode: String       // real | mock
    let providerName: String
}

enum PreflightDiagnostics {
    static func report(providerMode: String = "real",
                       providerName: String = "AppleEventKitProvider") -> PreflightReport {
        let ver = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
        let (backend, realtime) = health()
        return PreflightReport(
            appVersion: ver,
            appBuild: build,
            backendReachable: backend,
            realtimeAvailable: realtime,
            micPermission: String(describing: AudioCapture.micPermission()),
            calendarPermission: String(describing: AppleEventKitProvider().eventAccess()),
            remindersPermission: String(describing: AppleEventKitProvider().reminderAccess()),
            providerMode: providerMode,
            providerName: providerName
        )
    }

    /// GET /health → (backend reachable, realtime available). No secret transmitted.
    private static func health() -> (String, String) {
        guard let base = URL(string: RealtimeVoiceSession.backendBaseURL) else {
            return ("not_configured", "unavailable (no credential)")
        }
        let url = base.appendingPathComponent("health")
        var req = URLRequest(url: url)
        req.timeoutInterval = 3
        var backend = "unreachable"
        var realtime = "unavailable (no credential)"
        let sem = DispatchSemaphore(value: 0)
        URLSession.shared.dataTask(with: req) { data, resp, _ in
            if let r = resp as? HTTPURLResponse, (200..<300).contains(r.statusCode) {
                backend = "reachable"
                if let d = data,
                   let obj = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
                   let rt = obj["realtime"] as? String, rt == "available" {
                    realtime = "available"
                }
            }
            sem.signal()
        }.resume()
        _ = sem.wait(timeout: .now() + 4)
        return (backend, realtime)
    }
}
