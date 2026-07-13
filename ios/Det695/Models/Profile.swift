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
    let enabled: Bool
}

/// POST /profile/2fa/setup — the shared secret and otpauth URI for manual entry
/// into an authenticator app (we mirror the web's manual-entry flow; no QR).
struct TwoFASetupResponse: Decodable {
    let secret: String
    let otpauthUri: String
}

/// POST /profile/2fa/verify
struct TwoFAVerifyInput: Encodable {
    let code: String
}
