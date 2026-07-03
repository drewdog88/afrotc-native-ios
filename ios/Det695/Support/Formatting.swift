import Foundation

/// Display helpers for the string dates/times the API emits. The shared decoder
/// keeps all temporal fields as `String` (it has no date strategy), so parsing
/// for display happens here, defensively — an unparseable value falls back to
/// the raw string rather than throwing.
enum DateDisplay {
    /// Parse an ISO-8601 datetime like "2026-07-02T14:30:00Z" (with or without
    /// fractional seconds / offset).
    static func parseDateTime(_ raw: String) -> Date? {
        let withFrac = ISO8601DateFormatter()
        withFrac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = withFrac.date(from: raw) { return d }
        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        if let d = plain.date(from: raw) { return d }
        // Some servers omit the timezone; try a plain "yyyy-MM-dd'T'HH:mm:ss".
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return f.date(from: String(raw.prefix(19)))
    }

    /// Parse a bare "YYYY-MM-DD" date as a local calendar day.
    static func parseDay(_ raw: String) -> Date? {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f.date(from: String(raw.prefix(10)))
    }

    /// "Jul 2, 2026" from an ISO datetime or a bare day string.
    static func mediumDate(_ raw: String?) -> String {
        guard let raw, !raw.isEmpty else { return "—" }
        let date = parseDateTime(raw) ?? parseDay(raw)
        guard let date else { return raw }
        return date.formatted(.dateTime.month(.abbreviated).day().year())
    }

    /// "Jul 2, 2026 at 2:30 PM" from an ISO datetime.
    static func mediumDateTime(_ raw: String?) -> String {
        guard let raw, !raw.isEmpty else { return "—" }
        guard let date = parseDateTime(raw) else { return raw }
        return date.formatted(.dateTime.month(.abbreviated).day().year().hour().minute())
    }

    /// "2:30 PM" from an "HH:MM:SS" time string.
    static func time(_ raw: String?) -> String? {
        guard let raw, !raw.isEmpty else { return nil }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "HH:mm:ss"
        guard let date = f.date(from: raw) ?? {
            f.dateFormat = "HH:mm"; return f.date(from: raw)
        }() else { return raw }
        return date.formatted(.dateTime.hour().minute())
    }
}
