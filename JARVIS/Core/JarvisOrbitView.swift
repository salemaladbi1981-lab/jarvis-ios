import SwiftUI

/// V1 Agent Orbit — active agents فقط (لا 21 كرة دائمة).
/// Canvas واحد يرسم النقاط + handoff arc + name flash.
struct JarvisOrbitView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @ObservedObject var orbit: AgentOrbitModel
    var coreSize: CGFloat = 250
    var onTapAgent: (AgentOrbitItem) -> Void = { _ in }

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 60.0)) { timeline in
            let t = reduceMotion ? 0.0 : timeline.date.timeIntervalSinceReferenceDate
            Canvas { ctx, size in
                draw(canvas: &ctx, size: size, time: t)
            }
        }
        .allowsHitTesting(false)
        .accessibilityLabel("مدار الإيجنتات النشطة")
    }

    private func radiusFactor(_ group: String) -> Double {
        switch group {
        case "system":  return MotionTokens.Orbit.systemRadiusFactor
        case "content": return MotionTokens.Orbit.contentRadiusFactor
        default:        return MotionTokens.Orbit.coreRadiusFactor
        }
    }

    private func draw(canvas: inout GraphicsContext, size: CGSize, time: TimeInterval) {
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let baseRadius = min(size.width, size.height) / 2 - 30

        // handoff arc (طاقة من from إلى to)
        if let arc = orbit.handoffArc,
           let from = orbit.items.first(where: { $0.id == arc.from }),
           let to = orbit.items.first(where: { $0.id == arc.to }) {
            drawHandoffArc(canvas: &canvas, center: center, from: from, to: to, baseRadius: baseRadius, time: time)
        }

        // active agents
        for item in orbit.items {
            let rr = baseRadius * radiusFactor(item.group)
            let pos = CGPoint(x: center.x + cos(item.position) * rr,
                              y: center.y + sin(item.position) * rr)
            drawAgentDot(canvas: &canvas, at: pos, item: item, time: time)
        }
    }

    private func drawAgentDot(canvas: inout GraphicsContext, at pos: CGPoint, item: AgentOrbitItem, time: TimeInterval) {
        let r: CGFloat = 5.0
        // halo
        let halo = Path(ellipseIn: CGRect(x: pos.x - r * 2.4, y: pos.y - r * 2.4, width: r * 4.8, height: r * 4.8))
        canvas.fill(halo, with: .color(JarvisColor.primary_blue.opacity(MotionTokens.Orbit.agentHaloOpacity)))
        // dot (نبض خفيف)
        let pulse = reduceMotion ? 1.0 : 1.0 + 0.12 * sin(time * 2.0 + item.position)
        let dotR = r * CGFloat(pulse)
        let dot = Path(ellipseIn: CGRect(x: pos.x - dotR, y: pos.y - dotR, width: dotR * 2, height: dotR * 2))
        canvas.fill(dot, with: .color(JarvisColor.highlight_blue.opacity(0.95)))
        // name (صغير، خافت — ليس label دائم بارز)
        var text = canvas.resolve(Text(item.name).font(.system(size: 11)).foregroundColor(JarvisColor.text_muted))
        canvas.draw(text, at: CGPoint(x: pos.x, y: pos.y + r + 12))
    }

    private func drawHandoffArc(canvas: inout GraphicsContext, center: CGPoint,
                                from: AgentOrbitItem, to: AgentOrbitItem,
                                baseRadius: Double, time: TimeInterval) {
        let rf = radiusFactor(from.group)
        let rt = radiusFactor(to.group)
        let rFrom = baseRadius * rf
        let rTo = baseRadius * rt
        let pFrom = CGPoint(x: center.x + cos(from.position) * rFrom, y: center.y + sin(from.position) * rFrom)
        let pTo = CGPoint(x: center.x + cos(to.position) * rTo, y: center.y + sin(to.position) * rTo)
        // قوس ضوئي (منحنى بين النقطتين)
        var arc = Path()
        arc.move(to: pFrom)
        let mid = CGPoint(x: (pFrom.x + pTo.x) / 2, y: (pFrom.y + pTo.y) / 2)
        let dist = hypot(pTo.x - pFrom.x, pTo.y - pFrom.y)
        let ctrl = CGPoint(x: mid.x, y: mid.y - dist * 0.3)
        arc.addQuadCurve(to: pTo, control: ctrl)
        canvas.stroke(arc, with: .color(JarvisColor.highlight_blue.opacity(0.6)), lineWidth: 1.5)
    }
}
