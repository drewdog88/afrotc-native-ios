import Foundation

/// Request/response shapes for authentication, mirroring the backend schemas
/// (TokenPair, LoginRequest, UserOut). Decoded/encoded with the snake_case
/// strategies configured on `APIClient`, so properties stay camelCase here.

struct LoginRequest: Encodable {
    let username: String
    let password: String
    let totpCode: String?          // legacy; leave for compat, always nil now
    var trustToken: String? = nil
}

struct RefreshRequest: Encodable {
    let refreshToken: String
}

struct TokenPair: Decodable {
    let accessToken: String
    let refreshToken: String
    var forcePasswordChange: Bool = false
    var tokenType: String = "bearer"
}

/// POST /auth/refresh — the backend returns a fresh access token only; the
/// refresh token is not rotated, so the client keeps its stored one.
struct AccessToken: Decodable {
    let accessToken: String
    var tokenType: String = "bearer"
}

struct LoginResponse: Decodable {
    let accessToken: String?
    let refreshToken: String?
    var tokenType: String = "bearer"
    var forcePasswordChange: Bool = false
    var twoFactorRequired: Bool = false
    var method: String?
    var challengeToken: String?
}

enum LoginOutcome {
    case authenticated(TokenPair)
    case challenge(token: String, method: String)
}

struct LoginVerifyInput: Encodable {
    let challengeToken: String
    let code: String
    let trustDevice: Bool
}

struct LoginVerifyResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    var tokenType: String = "bearer"
    var forcePasswordChange: Bool = false
    var trustToken: String?
}

struct ResendInput: Encodable { let challengeToken: String }

struct UserOut: Decodable, Identifiable {
    let id: Int
    let username: String
    let email: String
    let firstName: String
    let lastName: String
    let fullName: String
    let role: String
    let isActive: Bool
    let isAdmin: Bool
    var phone: String?
    var isLocked: Bool = false  // defaulted so older payloads still decode
    var twoFactorEnabled: Bool = false
    var twoFactorMethod: String? = nil
    var twoFactorEnrollmentPrompted: Bool = false
    var is2faActive: Bool = false
}

// MARK: - Password reset (security-question flow)

/// POST /auth/forgot-password — identify an account by username or email.
struct ForgotPasswordRequest: Encodable {
    let username: String  // accepts username or email
}

/// The security question returned for a located account.
struct SecretQuestionOut: Decodable {
    let secretQuestion: String
}

/// POST /auth/reset-password — answer the question and set a new password.
struct ResetPasswordRequest: Encodable {
    let username: String
    let secretAnswer: String
    let newPassword: String
}
