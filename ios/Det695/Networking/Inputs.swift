import Foundation

/// Encodable request bodies for create/update mutations. The shared `APIClient`
/// encoder uses `.convertToSnakeCase`, so camelCase properties here map to the
/// backend's snake_case fields (e.g. `firstName` -> `first_name`).
///
/// Convention: **Create** inputs make the backend-required fields non-optional;
/// **Update** inputs make everything optional. `JSONEncoder` omits `nil`
/// optionals, so an Update body only sends the fields the caller set — matching
/// FastAPI's partial-update (PATCH) semantics. Callers must convert a cleared
/// text field to `nil` (not `""`) for optional email fields, which the backend
/// validates as `EmailStr`.

// MARK: - Recruit

struct RecruitCreateInput: Encodable {
    var firstName: String
    var lastName: String
    var currentSchool: String
    var schoolType: String = "high_school"
    var stage: String = "lead"
    var email: String?
    var phone: String?
    var major: String?
    var gpa: Double?
    var interests: String?
    var notes: String?
}

struct RecruitUpdateInput: Encodable {
    var firstName: String?
    var lastName: String?
    var currentSchool: String?
    var schoolType: String?
    var email: String?
    var phone: String?
    var major: String?
    var gpa: Double?
    var interests: String?
    var notes: String?
}

struct StageChangeInput: Encodable {
    var toStage: String
    var note: String?
}

// MARK: - Cadet

struct CadetCreateInput: Encodable {
    var firstName: String
    var lastName: String
    var email: String
    var major: String
    var graduationYear: Int
    var cadetRank: String
    var status: String = "active"
    var phone: String?
    var hometown: String?
    var officerInterest: String?
    var gpa: Double?
}

struct CadetUpdateInput: Encodable {
    var firstName: String?
    var lastName: String?
    var email: String?
    var major: String?
    var graduationYear: Int?
    var cadetRank: String?
    var status: String?
    var phone: String?
    var hometown: String?
    var officerInterest: String?
    var unenrollmentReason: String?
    var unenrollmentDate: String?
    var gpa: Double?
}

// MARK: - Contact

struct ContactCreateInput: Encodable {
    var universityName: String
    var contactName: String
    var email: String
    var isActive: Bool = true
    var contactTitle: String?
    var phone: String?
    var address: String?
    var notes: String?
}

struct ContactUpdateInput: Encodable {
    var universityName: String?
    var contactName: String?
    var email: String?
    var isActive: Bool?
    var contactTitle: String?
    var phone: String?
    var address: String?
    var notes: String?
}

// MARK: - Event

struct EventCreateInput: Encodable {
    var title: String
    var eventDate: String          // "YYYY-MM-DD"
    var eventType: String
    var status: String = "scheduled"
    var attendeesCount: Int = 0
    var description: String?
    var startTime: String?         // "HH:MM:SS"
    var endTime: String?           // "HH:MM:SS"
    var location: String?
    var universityId: Int?
    var notes: String?
}

struct EventUpdateInput: Encodable {
    var title: String?
    var eventDate: String?
    var eventType: String?
    var status: String?
    var attendeesCount: Int?
    var description: String?
    var startTime: String?
    var endTime: String?
    var location: String?
    var universityId: Int?
    var notes: String?
}

// MARK: - Follow-up

struct FollowUpCreateInput: Encodable {
    var note: String
    var dueDate: String            // ISO-8601 datetime
    var status: String = "open"
    var assigneeId: Int?
    var recruitId: Int?
    var contactId: Int?
}

struct FollowUpUpdateInput: Encodable {
    var note: String?
    var dueDate: String?
    var status: String?
    var assigneeId: Int?
    var recruitId: Int?
    var contactId: Int?
}
