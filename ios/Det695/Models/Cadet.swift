import Foundation

/// A commissioned/active cadet in the corps. Mirrors the backend `CadetOut`
/// schema; `status` is one of active / inactive / graduated (see Theme for the
/// dot color mapping).
struct CadetOut: Decodable, Identifiable {
    let id: Int
    let firstName: String
    let lastName: String
    let fullName: String
    let email: String
    let major: String
    let graduationYear: Int
    let cadetRank: String
    let status: String
    var gpa: Double?
    var hometown: String?
    var phone: String?
    var officerInterest: String?
    var unenrollmentReason: String?
    var unenrollmentDate: String?

    var statusLabel: String { status.prefix(1).uppercased() + status.dropFirst() }
}
