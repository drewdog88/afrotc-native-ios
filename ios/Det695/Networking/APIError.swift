import Foundation

/// Errors surfaced by `APIClient`. `.http` carries the status + a best-effort
/// human message pulled from the FastAPI `detail` field.
enum APIError: LocalizedError {
    case invalidResponse
    case unauthorized
    case http(status: Int, message: String)
    case decoding(String)
    case transport(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "The server sent an unexpected response."
        case .unauthorized: return "Your session has expired. Please sign in again."
        case let .http(status, message): return message.isEmpty ? "Request failed (\(status))." : message
        case let .decoding(detail): return "Couldn't read the server response. \(detail)"
        case let .transport(detail): return detail
        }
    }
}
