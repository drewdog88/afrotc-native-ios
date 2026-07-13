import Foundation

/// Admin user-management + activity-log shapes, mirroring the backend
/// `app/schemas/admin.py`. Encoded/decoded with the snake_case strategies on
/// `APIClient`, so properties stay camelCase here.

/// POST /admin/users — creates an account with a temporary password; the backend
/// forces a password change on first sign-in.
struct AdminUserCreate: Encodable {
    let username: String
    let email: String
    let password: String
    let firstName: String
    let lastName: String
    var phone: String?
    var role: String = "recruiter"
    let secretQuestion: String
    let secretAnswer: String
}

/// PATCH /admin/users/{id} — only the keys we send change (backend uses
/// `exclude_unset`). Role and active-state are the two the console edits inline.
struct AdminUserUpdate: Encodable {
    var role: String?
    var isActive: Bool?
    var isLocked: Bool?
    var password: String?
}

/// A single audit-log entry. Mirrors the backend `ActivityLogOut`; `createdAt`
/// arrives as an ISO-8601 string and is formatted for display via `DateDisplay`.
struct ActivityLogOut: Decodable, Identifiable {
    let id: Int
    let userId: Int
    let username: String
    let action: String
    var tableName: String?
    var recordId: Int?
    var recordDescription: String?
    var details: String?
    let createdAt: String
}
