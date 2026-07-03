import Foundation

/// A recruiter task. Mirrors the backend `FollowUpOut` schema. `status` is one of
/// open / done. Timestamps arrive as ISO-8601 strings and are kept as `String`.
struct FollowUpOut: Decodable, Identifiable {
    let id: Int
    let note: String
    let dueDate: String
    let status: String
    var completedAt: String?
    var assigneeId: Int?
    var createdById: Int?
    var recruitId: Int?
    var contactId: Int?
    var createdAt: String?
    var lastModified: String?

    var isDone: Bool { status.lowercased() == "done" }
}
