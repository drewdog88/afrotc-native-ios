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
/// `exclude_unset`). The console edits profile fields, role, active-state, and
/// can reset a password or clear a lockout.
struct AdminUserUpdate: Encodable {
    var firstName: String?
    var lastName: String?
    var email: String?
    var phone: String?
    var role: String?
    var isActive: Bool?
    var isLocked: Bool?
    var failedLoginAttempts: Int?
    var password: String?
    var twoFactorEnabled: Bool?
}

/// A single audit-log entry. Mirrors the backend `ActivityLogOut`; `createdAt`
/// arrives as an ISO-8601 string and is formatted for display via `DateDisplay`.
struct ActivityLogOut: Decodable, Identifiable {
    let id: Int
    let userId: Int?  // null for public/system actions (e.g. a public request-info submission)
    let username: String
    let action: String
    var tableName: String?
    var recordId: Int?
    var recordDescription: String?
    var details: String?
    let createdAt: String
}

/// GET /admin/intake-settings — decoded with .convertFromSnakeCase.
struct IntakeSettingsOut: Decodable {
    let id: Int
    var recruiterNotificationEmail: String?
    let ackEmailSubject: String
    let ackEmailBody: String
}

/// PUT /admin/intake-settings — only sent keys change (backend exclude_unset).
struct IntakeSettingsUpdate: Encodable {
    var recruiterNotificationEmail: String?
    var ackEmailSubject: String?
    var ackEmailBody: String?
}
