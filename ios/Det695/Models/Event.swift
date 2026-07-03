import Foundation

/// Status of a detachment outreach event. Decodes defensively so an unexpected
/// server value never crashes the list.
enum EventStatus: String, CaseIterable, Identifiable {
    case scheduled, completed, cancelled

    var id: String { rawValue }

    static func from(_ raw: String) -> EventStatus {
        EventStatus(rawValue: raw.lowercased()) ?? .scheduled
    }

    var label: String { rawValue.prefix(1).uppercased() + rawValue.dropFirst() }
}

/// A detachment outreach event. Mirrors the backend `EventOut` schema. Dates and
/// times arrive as plain strings (`event_date` = `YYYY-MM-DD`, `start_time` /
/// `end_time` = `HH:MM:SS`) and are kept as `String`.
struct EventOut: Decodable, Identifiable {
    let id: Int
    let title: String
    var description: String?
    let eventDate: String
    var startTime: String?
    var endTime: String?
    var location: String?
    var universityId: Int?
    let eventType: String
    let status: String
    let attendeesCount: Int
    var latitude: Double?
    var longitude: Double?
    var notes: String?

    var statusValue: EventStatus { .from(status) }
}
