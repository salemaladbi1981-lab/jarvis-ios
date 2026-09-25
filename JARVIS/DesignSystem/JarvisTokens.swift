//  Shared cinematic palette. Keep in sync with Resources/DESIGN-TOKENS.json.
//  Legacy blue-named aliases retain source compatibility; their palette is warm gold.
//
import SwiftUI

public extension Color {
    init(hex: String) {
        let s = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var n: UInt64 = 0
        Scanner(string: s).scanHexInt64(&n)
        self.init(red: Double((n >> 16) & 0xFF) / 255, green: Double((n >> 8) & 0xFF) / 255, blue: Double(n & 0xFF) / 255)
    }
}

public enum JarvisTypography {
    static let arabicFont = "IBM Plex Sans Arabic"
    static let arabicFallback = "Segoe UI, system-ui, sans-serif"
    static let englishDisplayFont = "Cormorant Garamond"
    static let englishDisplayFallback = "Georgia, serif"
    static let englishDisplayWeight = 600
    static let numerals = "western-tabular"
}

public enum JarvisColor {
    static let bg_0 = Color(hex: "#080706")
    static let bg_1 = Color(hex: "#15110D")
    static let surface = Color(hex: "#15110D")
    static let card = Color(hex: "#1D1812").opacity(0.45)
    static let border = Color(hex: "#CDA968").opacity(0.16)
    static let primary_blue = Color(hex: "#CDA968")
    static let highlight_blue = Color(hex: "#E9CF97")
    static let text_primary = Color(hex: "#F3EEE5")
    static let text_secondary = Color(hex: "#F3EEE5").opacity(0.72)
    static let text_muted = Color(hex: "#B9AD9A").opacity(0.82)
    static let success = Color(hex: "#63D9A0")
    static let warning_demo = Color(hex: "#F0B25F")
    static let danger = Color(hex: "#FF6B6B")
}

public enum JarvisTypeScale {
    static let display_jarvisDesktop: [CGFloat] = [30, 38]
    static let display_jarvisMobile: [CGFloat] = [22, 28]
    static let arabic_hero_titleDesktop: [CGFloat] = [30, 40]
    static let arabic_hero_titleMobile: [CGFloat] = [26, 34]
    static let section_titleDesktop: [CGFloat] = [18, 22]
    static let section_titleMobile: [CGFloat] = [16, 20]
    static let card_title: [CGFloat] = [15, 18]
    static let body: [CGFloat] = [13, 16]
    static let meta: [CGFloat] = [11, 13]
    static let compact_chip: [CGFloat] = [11, 13]
}

public enum JarvisGlass {
    static let panelFillOpacity: Double = 0.45
    static let panelBorderOpacity: Double = 0.16
    static let backdropBlur: CGFloat = 16
}

public enum JarvisRadius {
    static let card: CGFloat = 20
    static let control: CGFloat = 14
    static let pill: CGFloat = 999
    static let borderWidth: CGFloat = 1
}

public enum JarvisSpacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 24
    static let xxl: CGFloat = 32
    static let xxxl: CGFloat = 40
    static let xxxxl: CGFloat = 48
}

public enum JarvisGlow {
    static let primaryColor = Color(hex: "#CDA968")
    static let primaryOpacity: Double = 0.28
    static let primaryBlurRadius: Int = 18
    static let primarySpread: Int = 0
    static let primaryLayers: Int = 1
    static let activeIconColor = Color(hex: "#CDA968")
    static let activeIconOpacity: Double = 0.35
    static let activeIconBlurRadius: Int = 10
    static let activeIconSpread: Int = 0
    static let activeIconLayers: Int = 1
    static let coreColor = Color(hex: "#CDA968")
    static let coreOpacity: Double = 0.42
    static let coreBlurRadius: Int = 28
    static let coreSpread: Int = 6
    static let coreLayers: Int = 3
    static let agentActiveChipFill = Color(hex: "#1D1812").opacity(0.82)
    static let agentActiveChipBorder = Color(hex: "#CDA968")
    static let agentActiveNodeColor = Color(hex: "#E9CF97")
    static let agentActiveNodeOpacity: CGFloat = 1.0
    static let agentActiveGlowBlur: Int = 14
    static let agentActiveScale: Double = 1.04
    static let agentActiveRadialConnectionOpacity: Double = 0.28
    static let agentInactiveChipFill = Color(hex: "#1D1812").opacity(0.45)
    static let agentInactiveChipBorder = Color(hex: "#CDA968").opacity(0.16)
    static let agentInactiveNodeColor = Color(hex: "#CDA968").opacity(0.5)
    static let agentInactiveNodeOpacity: Double = 0.5
    static let agentInactiveGlowBlur: Int = 0
    static let agentInactiveScale: CGFloat = 1.0
    static let agentInactiveRadialConnectionOpacity: CGFloat = 0.0
    static let cardsDefaultShadowOpacity: CGFloat = 0.0
    static let cardsDefaultBorderOpacity: Double = 0.16
    static let cardsDefaultSurfaceOpacity: Double = 0.45
}

public enum JarvisIcon {
    static let strokeWidth: CGFloat = 1.5
    static let xs: CGFloat = 14
    static let sm: CGFloat = 18
    static let md: CGFloat = 22
    static let lg: CGFloat = 28
    static let activeColor = Color(hex: "#E9CF97").opacity(0.95)
    static let inactiveColor = Color(hex: "#B9AD9A").opacity(0.82)
}

public enum JarvisMotion {
    static let micro: Double = 0.15
    static let control: Double = 0.22
    static let groupTransition: Double = 0.48
    static let panelReveal: Double = 0.32
    static let coreIdlePulse: Double = 3.2
}

public enum JarvisOrbit {
    static let coreNodes = 8
    static let systemNodes = 5
    static let contentNodes = 8
    static let transitionMin: Double = 0.35
    static let transitionMax: Double = 0.6
}

public enum JarvisStateKey {
    static let all: [String] = ["خامل", "استماع", "تفكير", "يتكلم", "تنفيذ", "تنبيه", "موافقة"]
}

public enum JarvisStateBehavior {
    static let خامل = "low core motion, low waveform, soft glow"
    static let استماع = "waveform reacts to input, stronger gold pulse"
    static let تفكير = "orbital motion increases, waveform reduces"
    static let يتكلم = "waveform follows speech, core pulse tracks energy"
    static let تنفيذ = "active target card/agent indicates execution"
    static let تنبيه = "restrained warning emphasis, no full recolor"
    static let موافقة = "execution pauses, clear approval indicator"
}
