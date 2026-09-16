import SwiftUI

/// Level-driven waveform — يعكس mic/output حقيقي (لا sin زمني وهمي).
/// Listening → mic level؛ Speaking → output level؛ غير ذلك → شبه ساكن (بلا حركة صوتية وهمية).
struct WaveformView: View {
    @ObservedObject var levels: VisualLevelModel
    var state: JarvisState = .idle
    private let barCount = 40

    var body: some View {
        let level = activeLevel
        HStack(spacing: 2) {
            ForEach(0..<barCount, id: \.self) { i in
                Capsule()
                    .fill(JarvisColor.primary_blue.opacity(0.65))
                    .frame(width: 2.5, height: height(for: i, level: level))
            }
        }
        .frame(height: 40)
        .animation(.easeOut(duration: MotionTokens.Smoothing.attack), value: level)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private var activeLevel: Double {
        switch state {
        case .listening: return MotionTokens.Level.perceptual(levels.micLevel)
        case .speaking:  return MotionTokens.Level.perceptual(levels.outputLevel)
        default:         return 0
        }
    }

    private func height(for i: Int, level: Double) -> CGFloat {
        // وزن ثابت لكل شريط (شكل المغلف فقط — لا يتغير مع الزمن)
        let w = 0.25 + 0.75 * abs(sin(Double(i) / Double(barCount - 1) * .pi))
        let h = 3.0 + level * 34.0 * w
        return max(3.0, CGFloat(h))
    }
}
