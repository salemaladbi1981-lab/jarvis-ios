import Foundation
import Combine

/// V1 Visual — lightweight audio level model.
/// يعزل الـ high-frequency RMS (mic/output) عن HomeViewModel:
/// الـ JarvisCoreView فقط يراقب هذا model، ولا يُعاد بناء Home hierarchy كامل.
@MainActor
final class VisualLevelModel: ObservableObject {
    @Published var micLevel: Double = 0
    @Published var outputLevel: Double = 0

    // instrumentation: publishes/sec + peak (تشخيص، لا UI state)
    var micPublishCount = 0
    var outputPublishCount = 0
    var micLevelPeak: Double = 0
    var outputLevelPeak: Double = 0

    func setMicLevel(_ level: Double) {
        micPublishCount += 1
        if level > micLevelPeak { micLevelPeak = level }
        micLevel = level
    }
    func setOutputLevel(_ level: Double) {
        outputPublishCount += 1
        if level > outputLevelPeak { outputLevelPeak = level }
        outputLevel = level
    }

    /// Evidence string — يُقرأ من Xcode console (يُستدعى عند response.done أو يدوياً).
    func evidence() -> String {
        "LEVELS micPublishes=\(micPublishCount) outPublishes=\(outputPublishCount) micPeak=\(String(format: "%.3f", micLevelPeak)) outPeak=\(String(format: "%.3f", outputLevelPeak))"
    }
}
