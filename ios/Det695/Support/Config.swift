import Foundation

/// Static configuration. The API base URL defaults to a local backend and can
/// be overridden at launch with the `DET695_API_BASE` environment variable
/// (Scheme → Run → Arguments → Environment Variables) or by editing `default`.
///
/// On the iOS Simulator, `localhost` reaches the Mac host, so a backend started
/// with `uv run uvicorn app.main:app --port 8099` from `backend/` is reachable
/// at the default below. For a physical device, point this at your Mac's LAN IP
/// (e.g. http://192.168.1.20:8099/api/v1) or a deployed URL.
enum Config {
    static let apiBaseURL: URL = {
        let fallback = "http://localhost:8099/api/v1"
        let raw = ProcessInfo.processInfo.environment["DET695_API_BASE"] ?? fallback
        return URL(string: raw) ?? URL(string: fallback)!
    }()
}
