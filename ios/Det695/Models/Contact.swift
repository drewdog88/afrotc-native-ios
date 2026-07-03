import Foundation

/// A university/high-school point of contact the detachment recruits through.
/// Mirrors the backend `ContactOut` schema. Timestamps arrive as ISO-8601
/// strings and are kept as `String` (the shared decoder has no date strategy —
/// see the note in `APIClient`).
struct ContactOut: Decodable, Identifiable {
    let id: Int
    let universityName: String
    let contactName: String
    var contactTitle: String?
    let email: String
    var phone: String?
    var address: String?
    var notes: String?
    let isActive: Bool
    var latitude: Double?
    var longitude: Double?
    var createdAt: String?
    var lastModified: String?
}
