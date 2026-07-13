import Foundation

/// An external web link in the materials library. Mirrors the backend `LinkOut`
/// schema. `createdAt` / `lastModified` are non-null here (unlike Contacts).
struct LinkOut: Decodable, Identifiable {
    let id: Int
    let title: String
    let url: String
    var description: String?
    let category: String
    let isActive: Bool
    let sortOrder: Int
    let createdAt: String
    let lastModified: String

    /// Host shown next to the title, e.g. "afrotc.com".
    var host: String { URL(string: url)?.host ?? url }
}

/// An uploaded document's metadata. Mirrors the backend `DocumentOut` schema —
/// the raw bytes are fetched separately via the download endpoint.
struct DocumentOut: Decodable, Identifiable {
    let id: Int
    let title: String
    var description: String?
    let filename: String
    let originalFilename: String
    var fileSize: Int?
    var fileType: String?
    let category: String
    let isActive: Bool
    let sortOrder: Int
    let createdAt: String
    let lastModified: String

    /// Human byte size, e.g. "2.4 MB".
    var sizeLabel: String {
        guard let bytes = fileSize else { return "—" }
        return ByteCountFormatter.string(fromByteCount: Int64(bytes), countStyle: .file)
    }
}

/// POST /materials/links — the encoder's `.convertToSnakeCase` maps these to the
/// backend's `LinkCreate` (url is validated as an HttpUrl server-side).
struct LinkCreateInput: Encodable {
    let title: String
    let url: String
    var description: String?
    var category: String = "general"
    var isActive: Bool = true
    var sortOrder: Int = 0
}

/// PATCH /materials/links/{id} — only the keys we send are changed
/// (backend dumps with `exclude_unset`).
struct LinkUpdateInput: Encodable {
    var title: String?
    var url: String?
    var description: String?
    var category: String?
    var isActive: Bool?
    var sortOrder: Int?
}
