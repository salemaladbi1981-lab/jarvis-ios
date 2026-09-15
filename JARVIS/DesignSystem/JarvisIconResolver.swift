import Foundation

/// Maps canonical icon IDs (ICON-MAP.md) to native SF Symbols that are
/// visually equivalent. Priority: custom vector asset > equivalent SF Symbol
/// > documented fallback. See P2_2_ICON_PARITY.md for the mapping table.
enum JarvisIconResolver {
    static func symbol(for iconID: String) -> String {
        switch iconID {
        // Navigation
        case "nav.home":        return "house.fill"
        case "nav.devices":     return "square.grid.2x2.fill"
        case "nav.car":         return "car.fill"
        case "nav.more":        return "ellipsis"
        // Smart Home
        case "home.light":      return "lightbulb.fill"
        case "home.ac":         return "snowflake"
        case "home.curtains":   return "curtains.closed"
        case "home.tv":         return "tv.fill"
        // Security
        case "sec.shield":      return "shield.fill"
        case "sec.camera":      return "video.fill"
        case "sec.lock":        return "lock.fill"
        // Media
        case "media.previous":  return "backward.fill"
        case "media.play":      return "play.fill"
        case "media.pause":     return "pause.fill"
        case "media.next":      return "forward.fill"
        // Utility
        case "util.search":     return "magnifyingglass"
        case "util.bell":       return "bell.fill"
        case "util.profile":    return "person.crop.circle.fill"
        case "util.mic":        return "mic.fill"
        case "util.send":       return "paperplane.fill"
        case "util.location":   return "location.fill"
        case "util.waveform":   return "waveform"
        case "util.alert":      return "exclamationmark.triangle.fill"
        // fallback (documented)
        default:                return "circle"
        }
    }
}
