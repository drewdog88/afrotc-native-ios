import Foundation

/// Generic paged list envelope used by the list endpoints
/// (Page[RecruitOut], Page[CadetOut]): { items, total, skip, limit }.
struct Page<T: Decodable>: Decodable {
    let items: [T]
    let total: Int
    let skip: Int
    let limit: Int
}
