import SwiftUI

/// Native Jarvis core — luminous center, intersecting rings, particles.
/// All colors from generated JarvisColor tokens. Deterministic geometry.
struct JarvisCoreView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var state: JarvisState = .idle
    var size: CGFloat = 250

    private let particles: [CGPoint] = [
        CGPoint(x: 0.20, y: -0.60), CGPoint(x: -0.55, y: -0.30), CGPoint(x: 0.65, y: -0.15),
        CGPoint(x: -0.25, y: 0.65), CGPoint(x: 0.45, y: 0.55), CGPoint(x: -0.70, y: 0.10),
        CGPoint(x: 0.05, y: -0.80), CGPoint(x: 0.80, y: 0.30), CGPoint(x: -0.45, y: -0.70),
        CGPoint(x: 0.35, y: 0.80), CGPoint(x: -0.85, y: -0.10), CGPoint(x: 0.60, y: 0.60),
        CGPoint(x: -0.60, y: 0.55), CGPoint(x: 0.15, y: 0.15), CGPoint(x: -0.10, y: -0.45),
    ]
    private let ringAngles: [Double] = [0, 30, 60, 105]
    private let ringRadii: [CGFloat] = [0.62, 0.72, 0.82, 0.90]

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 60.0)) { timeline in
            let t = reduceMotion ? 0.0 : timeline.date.timeIntervalSinceReferenceDate
            Canvas { ctx, size in
                draw(canvas: &ctx, size: size, time: t)
            }
        }
        .frame(width: size, height: size)
        .accessibilityLabel("نواة جارفس")
    }

    private func draw(canvas: inout GraphicsContext, size: CGSize, time: TimeInterval) {
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let radius = min(size.width, size.height) / 2

        // 1. Outer bloom
        let bloomOps: [Double] = [0.12, 0.08, 0.05]
        for (i, op) in bloomOps.enumerated() {
            let rr = radius * (0.9 - Double(i) * 0.08)
            let g = GraphicsContext.Shading.radialGradient(
                Gradient(colors: [
                    JarvisColor.highlight_blue.opacity(op),
                    JarvisColor.primary_blue.opacity(op * 0.6),
                    .clear,
                ]),
                center: center, startRadius: 0, endRadius: rr
            )
            let path = Path(ellipseIn: CGRect(x: center.x - rr, y: center.y - rr, width: rr * 2, height: rr * 2))
            canvas.fill(path, with: g)
        }

        // 2. Luminous center
        let coreRadius = radius * 0.42
        let coreGrad = GraphicsContext.Shading.radialGradient(
            Gradient(colors: [
                Color.white.opacity(0.95),
                JarvisColor.highlight_blue.opacity(0.8),
                JarvisColor.primary_blue.opacity(0.35),
                JarvisColor.primary_blue.opacity(0.0),
            ]),
            center: center, startRadius: 0, endRadius: coreRadius
        )
        let corePath = Path(ellipseIn: CGRect(x: center.x - coreRadius, y: center.y - coreRadius, width: coreRadius * 2, height: coreRadius * 2))
        canvas.fill(corePath, with: coreGrad)

        // 3. Intersecting orbital rings
        let pulse = reduceMotion ? 1.0 : 1.0 + 0.03 * sin(time * 1.4)
        for (i, angleDeg) in ringAngles.enumerated() {
            let rr = radius * ringRadii[i] * pulse
            let angle = Angle.degrees(angleDeg + (reduceMotion ? 0 : Double(i) * 4))
            var ring = Path()
            ring.addEllipse(in: CGRect(x: center.x - rr, y: center.y - rr * 0.55, width: rr * 2, height: rr * 1.1))
            let rot = CGAffineTransform(translationX: center.x, y: center.y)
                .rotated(by: CGFloat(angle.radians))
                .translatedBy(x: -center.x, y: -center.y)
            ring = ring.applying(rot)
            canvas.stroke(ring, with: .color(JarvisColor.primary_blue.opacity(0.5)), lineWidth: 1.2)
        }

        // 4. Particles
        let pr = radius * 0.98
        for (i, p) in particles.enumerated() {
            let wobble = reduceMotion ? 0.0 : 0.04 * sin(time * 2.0 + Double(i))
            let px = center.x + p.x * pr
            let py = center.y + p.y * pr * (1.0 + wobble)
            let dot = Path(ellipseIn: CGRect(x: px - 1.4, y: py - 1.4, width: 2.8, height: 2.8))
            canvas.fill(dot, with: .color(JarvisColor.highlight_blue.opacity(0.7)))
        }
    }
}
