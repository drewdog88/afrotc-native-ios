import SwiftUI

/// Brand palette mirrored from the web app's design tokens (web/src/styles/tokens.css)
/// so the two clients read as one product.
enum Theme {
    static let ink = Color(hex: 0x0E1B2C)      // dark navy — sidebar / primary text
    static let accent = Color(hex: 0xF2A83B)   // amber-gold — accent / beacon
    static let ok = Color(hex: 0x2F8F6B)       // green — active / healthy
    static let danger = Color(hex: 0xB4563F)   // warm red — inactive / warning
    static let muted = Color(hex: 0x64748B)    // slate gray — secondary

    /// Ordered stage palette for the recruiting funnel, matching the web dashboard
    /// (apex gold → cool lead gray).
    static func stageColor(_ stage: RecruitStage) -> Color {
        switch stage {
        case .commissioned: return accent
        case .enrolled: return ok
        case .applied: return Color(hex: 0x6AA9D8)
        case .contacted: return Color(hex: 0x3B6EA5)
        case .lead: return muted
        case .declined: return danger
        }
    }

    /// Status dot color for a cadet, matching the web Cadets page
    /// (active=green, inactive=red, graduated=gold).
    static func cadetStatusColor(_ status: String) -> Color {
        switch status.lowercased() {
        case "active": return ok
        case "inactive": return danger
        case "graduated": return accent
        default: return muted
        }
    }

    /// Status dot color for an event, matching the web Events page
    /// (scheduled=sky, completed=green, cancelled=red).
    static func eventStatusColor(_ status: EventStatus) -> Color {
        switch status {
        case .scheduled: return Color(hex: 0x3B6EA5)
        case .completed: return ok
        case .cancelled: return danger
        }
    }
}

extension Color {
    /// Build a Color from a 0xRRGGBB integer literal.
    init(hex: UInt32, opacity: Double = 1) {
        let r = Double((hex >> 16) & 0xFF) / 255
        let g = Double((hex >> 8) & 0xFF) / 255
        let b = Double(hex & 0xFF) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: opacity)
    }
}
