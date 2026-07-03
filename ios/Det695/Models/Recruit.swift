import Foundation

/// The recruiting funnel, ordered first-contact → commissioning. Mirrors the
/// backend `RecruitStage` enum. `.from(_:)` decodes defensively so an unexpected
/// server value never crashes the list.
enum RecruitStage: String, CaseIterable, Identifiable {
    case lead, contacted, applied, enrolled, commissioned, declined

    var id: String { rawValue }

    static func from(_ raw: String) -> RecruitStage {
        RecruitStage(rawValue: raw.lowercased()) ?? .lead
    }

    var label: String {
        switch self {
        case .lead: return "Lead"
        case .contacted: return "Contacted"
        case .applied: return "Applied"
        case .enrolled: return "Enrolled"
        case .commissioned: return "Commissioned"
        case .declined: return "Declined"
        }
    }

    /// Ordering used by the funnel display (apex first).
    var funnelOrder: Int {
        switch self {
        case .commissioned: return 0
        case .enrolled: return 1
        case .applied: return 2
        case .contacted: return 3
        case .lead: return 4
        case .declined: return 5
        }
    }
}

struct RecruitOut: Decodable, Identifiable {
    let id: Int
    let firstName: String
    let lastName: String
    let fullName: String
    let currentSchool: String
    let schoolType: String
    let stage: String
    var email: String?
    var phone: String?
    var gpa: Double?
    var major: String?
    var interests: String?
    var notes: String?

    var stageValue: RecruitStage { .from(stage) }
}
