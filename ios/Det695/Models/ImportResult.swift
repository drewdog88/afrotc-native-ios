import Foundation

/// Result of a bulk recruit import, mirroring the backend `ImportResult`
/// (app/schemas/imports.py). Decoded with the snake_case strategy on `APIClient`.
struct ImportResult: Decodable {
    let totalRows: Int
    let imported: Int
    let failed: Int
    let errors: [ImportRowError]
}

/// One row that failed validation, with its 1-indexed row number and messages.
struct ImportRowError: Decodable, Identifiable {
    let row: Int
    let errors: [String]

    var id: Int { row }
}
