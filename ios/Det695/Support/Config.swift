import Foundation

/// Static configuration. The API base URL defaults to the deployed production
/// backend so the app works out of the box on any simulator or device. It can
/// be overridden at launch with the `DET695_API_BASE` environment variable
/// (Scheme → Run → Arguments → Environment Variables) — e.g. point it at a
/// local backend (`http://localhost:8099/api/v1`, reachable from the iOS
/// Simulator when you run `uv run uvicorn app.main:app --port 8099` from
/// `backend/`) or your Mac's LAN IP for a physical device on the same network.
enum Config {
    static let apiBaseURL: URL = {
        let fallback = "https://afrotc-native-ios.vercel.app/api/v1"
        let raw = ProcessInfo.processInfo.environment["DET695_API_BASE"] ?? fallback
        return URL(string: raw) ?? URL(string: fallback)!
    }()
}
