import Foundation

/// Self-service profile + 2FA payloads, mirroring the web's Profile page contract
/// (web/src/pages/Profile.tsx). The encoder uses `.convertToSnakeCase`, so Swift
/// camelCase maps to the backend's snake_case fields.

/// PATCH /profile — any field omitted (nil) is left unchanged by the backend
/// (it dumps with `exclude_unset`). We only send keys the user actually edited.
struct ProfileUpdate: Encodable {
    var firstName: String?
    var lastName: String?
    var email: String?
    var phone: String?
}

/// POST /auth/change-password
struct PasswordChangeInput: Encodable {
    let currentPassword: String
    let newPassword: String
}

/// GET /profile/2fa
struct TwoFAStatus: Decodable {
    var enabled: Bool = false
    var method: String? = nil
    var enrollmentPrompted: Bool = false
}

/// POST /profile/2fa/enroll
struct TwoFAEnrollInput: Encodable { let method: String }         // "email"

/// POST /profile/2fa/enroll/verify
struct TwoFAEnrollVerifyInput: Encodable { let code: String }

/// A device the user has chosen to trust, skipping 2FA challenges for a
/// limited window. Date fields arrive as ISO-8601 strings; the shared
/// `APIClient` decoder has no `dateDecodingStrategy` configured, so these
/// stay `String` and are formatted for display via `DateDisplay`.
struct TrustedDevice: Decodable, Identifiable {
    let id: Int
    let deviceLabel: String
    let createdAt: String
    let lastUsedAt: String
    let expiresAt: String
}
