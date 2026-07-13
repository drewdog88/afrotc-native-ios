import Foundation

/// Request/response shapes for authentication, mirroring the backend schemas
/// (TokenPair, LoginRequest, UserOut). Decoded/encoded with the snake_case
/// strategies configured on `APIClient`, so properties stay camelCase here.

struct LoginRequest: Encodable {
    let username: String
    let password: String
    let totpCode: String?
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
