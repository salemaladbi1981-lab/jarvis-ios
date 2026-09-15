import SwiftUI

/// Mock waveform driven by JarvisState.
struct WaveformView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var state: JarvisState = .idle
    private let barCount = 40

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
            let t = reduceMotion ? 0.0 : timeline.date.timeIntervalSinceReferenceDate
            HStack(spacing: 2) {
                ForEach(0..<barCount, id: \.self) { i in
                    Capsule()
                        .fill(JarvisColor.primary_blue.opacity(0.65))
                        .frame(width: 2.5, height: height(for: i, time: t))
                }
            }
            .frame(height: 40)
        }
        .accessibilityHidden(true)
    }

    private func height(for i: Int, time: Double) -> CGFloat {
        let base: Double
        switch state {
        case .idle:      base = 0.15
        case .listening: base = 0.70
        case .thinking:  base = 0.35
        case .speaking:  base = 0.80
        case .executing: base = 0.40
        case .alert:     base = 0.50
        case .approval:  base = 0.20
        }
        let phase = sin(Double(i) * 0.7 + time * 3.0)
        let h = 6.0 + base * 30.0 * (0.5 + 0.5 * phase)
        return max(3.0, CGFloat(h))
    }
}
