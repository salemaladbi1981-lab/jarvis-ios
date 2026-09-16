import SwiftUI

/// V1 Living Core — motion مشتق من Runtime State + audio level (لا sine mock لـ listening/speaking).
/// Idle فقط يستخدم sine breathing. Listening/Speaking يستخدمان level حقيقي (smoothed إلى 60fps).
struct JarvisCoreView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var state: JarvisState = .idle
    var micLevel: Double = 0.0          // normalized 0..1 (target)
    var outputLevel: Double = 0.0       // normalized 0..1 (target)
    var successPulse: Bool = false      // transient success (tool.completed)
    var size: CGFloat = 250
    var onFrameTime: ((Double) -> Void)? = nil   // FPS instrumentation

    @State private var smoothedMic: Double = 0.0
    @State private var smoothedOutput: Double = 0.0
    @State private var successAnim: Double = 0.0

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
                let start = CACurrentMediaTime()
                draw(canvas: &ctx, size: size, time: t,
                     mic: smoothedMic, output: smoothedOutput,
                     success: successAnim)
                let frameMs = (CACurrentMediaTime() - start) * 1000
                onFrameTime?(frameMs)
            }
        }
        .frame(width: size, height: size)
        .allowsHitTesting(false)
        .onChange(of: micLevel) { v in
            withAnimation(.easeOut(duration: MotionTokens.Smoothing.attack)) { smoothedMic = v }
        }
        .onChange(of: outputLevel) { v in
            withAnimation(.easeOut(duration: MotionTokens.Smoothing.attack)) { smoothedOutput = v }
        }
        .onChange(of: successPulse) { p in
            if p { withAnimation(.easeOut(duration: MotionTokens.Duration.successPulse)) { successAnim = 1.0 } }
        }
        .onChange(of: successAnim) { v in
            if v >= 1.0 { withAnimation(.easeOut(duration: MotionTokens.Duration.successPulse)) { successAnim = 0.0 } }
        }
        .onAppear { LaunchTiming.mark("core onAppear") }
        .accessibilityLabel("نواة جارفس")
    }

    // MARK: draw

    private func draw(canvas: inout GraphicsContext, size: CGSize, time: TimeInterval,
                      mic: Double, output: Double, success: Double) {
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let radius = min(size.width, size.height) / 2
        let reduce = reduceMotion

        // disturbance (error) — إزاحة خفيفة بلا flashing أحمر
        var offset = CGSize.zero
        var bloomBoost = 0.0
        if state == .alert && !reduce {
            offset = CGSize(width: MotionTokens.Amplitude.errorShake * radius * sin(time * 40),
                            height: 0)
        }
        // success bloom
        if success > 0 {
            bloomBoost = success * 0.5
        }

        let c = CGPoint(x: center.x + offset.width, y: center.y + offset.height)

        // 1. Outer bloom (state+level modulated)
        let bloomOps: [Double] = [0.12, 0.08, 0.05]
        for (i, op) in bloomOps.enumerated() {
            let rr = radius * (0.9 - Double(i) * 0.08) * (1 + bloomBoost * Double(i) * 0.05)
            let g = GraphicsContext.Shading.radialGradient(
                Gradient(colors: [
                    JarvisColor.highlight_blue.opacity(op + bloomBoost),
                    JarvisColor.primary_blue.opacity(op * 0.6),
                    .clear,
                ]),
                center: c, startRadius: 0, endRadius: rr
            )
            let path = Path(ellipseIn: CGRect(x: c.x - rr, y: c.y - rr, width: rr * 2, height: rr * 2))
            canvas.fill(path, with: g)
        }

        // 2. Luminous center — scale حسب state + level
        var coreScale = 1.0
        if !reduce {
            switch state {
            case .idle:
                coreScale = 1.0 + MotionTokens.Amplitude.idleBreath * sin(time * 2 * .pi / MotionTokens.Duration.idleBreath)
            case .listening:
                coreScale = 1.0 + MotionTokens.Amplitude.listening * mic
            case .speaking:
                coreScale = 1.0 + MotionTokens.Amplitude.speaking * output
            case .thinking:
                coreScale = 1.0 + MotionTokens.Amplitude.thinking * 0.5 * (1 + sin(time * 2 * .pi * MotionTokens.Speed.thinking))
            case .executing:
                coreScale = 1.0 + MotionTokens.Amplitude.executing * 0.5
            case .alert, .approval:
                coreScale = 1.0
            }
        }
        let coreRadius = radius * 0.42 * coreScale
        let coreGrad = GraphicsContext.Shading.radialGradient(
            Gradient(colors: [
                Color.white.opacity(0.95),
                JarvisColor.highlight_blue.opacity(0.8),
                JarvisColor.primary_blue.opacity(0.35),
                JarvisColor.primary_blue.opacity(0.0),
            ]),
            center: c, startRadius: 0, endRadius: coreRadius
        )
        let corePath = Path(ellipseIn: CGRect(x: c.x - coreRadius, y: c.y - coreRadius, width: coreRadius * 2, height: coreRadius * 2))
        canvas.fill(corePath, with: coreGrad)

        // 3. Intersecting rings — rotation (thinking/executing أسرع)
        var rotSpeed = 0.0
        if !reduce {
            switch state {
            case .thinking: rotSpeed = MotionTokens.Speed.thinking * 2 * .pi
            case .executing: rotSpeed = MotionTokens.Speed.executing * 2 * .pi
            default: rotSpeed = 0.02   // بطيء جداً
            }
        }
        let pulse = reduce ? 1.0 : 1.0 + 0.02 * (state == .listening ? mic : (state == .speaking ? output : 0))
        for (i, angleDeg) in ringAngles.enumerated() {
            let rr = radius * ringRadii[i] * CGFloat(pulse)
            let angle = Angle.degrees(angleDeg + Double(i) * 4 + time * rotSpeed)
            var ring = Path()
            ring.addEllipse(in: CGRect(x: c.x - rr, y: c.y - rr * 0.55, width: rr * 2, height: rr * 1.1))
            let rot = CGAffineTransform(translationX: c.x, y: c.y)
                .rotated(by: CGFloat(angle.radians))
                .translatedBy(x: -c.x, y: -c.y)
            ring = ring.applying(rot)
            canvas.stroke(ring, with: .color(JarvisColor.primary_blue.opacity(0.5)), lineWidth: 1.2)
        }

        // 4. Particles — listening: energy داخلة (من الحواف)؛ executing: تدور أسرع
        let pr = radius * 0.98
        for (i, p) in particles.enumerated() {
            var px = c.x + p.x * pr
            var py = c.y + p.y * pr
            if !reduce {
                if state == .listening {
                    // طاقة تدخل للنواة حسب mic level
                    let inward = 1.0 - mic * 0.5
                    px = c.x + p.x * pr * inward
                    py = c.y + p.y * pr * inward
                } else if state == .executing {
                    let a = atan2(p.y, p.x) + time * MotionTokens.Speed.executing * 2 * .pi
                    let rr = pr
                    px = c.x + cos(a) * rr
                    py = c.y + sin(a) * rr
                } else {
                    let wobble = 0.04 * sin(time * 2.0 + Double(i))
                    py = c.y + p.y * pr * (1.0 + wobble)
                }
            }
            let dot = Path(ellipseIn: CGRect(x: px - 1.4, y: py - 1.4, width: 2.8, height: 2.8))
            canvas.fill(dot, with: .color(JarvisColor.highlight_blue.opacity(0.7)))
        }
    }
}
