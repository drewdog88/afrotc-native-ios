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
