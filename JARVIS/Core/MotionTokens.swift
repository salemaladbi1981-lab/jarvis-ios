import Foundation
import SwiftUI

/// V1 Motion tokens — central, tunable. Baseline values only (قابلة للتعديل بعد Physical Review).
/// لا تُعدَّل الـ architecture لتغيير قيمة؛ عدِّل الـ token هنا فقط.
enum MotionTokens {
    // MARK: Duration (seconds)
    enum Duration {
        static let idleBreath: Double = 4.0
        static let agentEnter: Double = 0.30
        static let agentExit: Double = 0.25
        static let handoff: Double = 0.35
        static let successPulse: Double = 0.40
        static let errorDisturbance: Double = 0.30
        static let bargeStop: Double = 0.10
        static let nameFlash: Double = 1.2
    }

    // MARK: Amplitude (نسبة من radius / normalized)
    enum Amplitude {
        static let idleBreath: Double = 0.03
        static let listening: Double = 0.25      // مضروب بـ micLevel
        static let speaking: Double = 0.08       // مضروب بـ outputLevel
        static let thinking: Double = 0.15
        static let executing: Double = 0.12
        static let errorShake: Double = 0.02
    }

    // MARK: Speed
    enum Speed {
        static let thinking: Double = 0.5        // rev/s
        static let executing: Double = 1.2       // rev/s
        static let idleInternal: Double = 0.2    // deg/frame
    }

    // MARK: Smoothing (RMS → 60fps interpolation)
    enum Smoothing {
        static let attack: Double = 0.10   // أسرع ارتفاع (استجابة للصوت)
        static let release: Double = 0.35  // أبطأ انخفاض (تجنب flicker)
    }

    // MARK: Orbit
    enum Orbit {
        static let coreRadiusFactor: Double = 1.0
        static let systemRadiusFactor: Double = 1.35
        static let contentRadiusFactor: Double = 1.70
        static let agentHaloOpacity: Double = 0.35
    }
}

/// Easing helpers (لا نعتمد على SwiftUI default في الـ Canvas).
enum MotionEasing {
    static func easeOutCubic(_ t: Double) -> Double { 1 - pow(1 - t, 3) }
    static func easeInCubic(_ t: Double) -> Double { t * t * t }
    static func easeInOutSine(_ t: Double) -> Double { 0.5 - 0.5 * cos(.pi * t) }
    static func easeOutExpo(_ t: Double) -> Double { t >= 1 ? 1 : 1 - pow(2, -10 * t) }
}
