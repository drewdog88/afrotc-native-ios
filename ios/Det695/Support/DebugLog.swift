import Foundation
import os

/// Thin wrapper over `os.Logger` whose calls are compiled out entirely in
/// release builds. Used by the networking and Keychain layers for debug tracing
/// (request/response, Keychain OSStatus) — useful in the Simulator/DEBUG, and
/// zero cost with no log noise in a shipped TestFlight/App Store build.
///
/// Stream it in DEBUG with:
///   xcrun simctl spawn booted log stream \
///     --predicate 'subsystem == "com.det695.recruiting"'
struct DebugLog {
    #if DEBUG
    private let logger: Logger
    init(category: String) {
        logger = Logger(subsystem: "com.det695.recruiting", category: category)
    }
    func notice(_ message: @autoclosure () -> String) {
        let text = message()
        logger.notice("\(text, privacy: .public)")
    }
    func error(_ message: @autoclosure () -> String) {
        let text = message()
        logger.error("\(text, privacy: .public)")
    }
    #else
    init(category: String) {}
    @inline(__always) func notice(_ message: @autoclosure () -> String) {}
    @inline(__always) func error(_ message: @autoclosure () -> String) {}
    #endif
}
