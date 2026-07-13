import Foundation

/// Async client over the FastAPI backend. Holds the JWT access/refresh pair in
/// the Keychain, attaches the bearer token, and transparently refreshes once on
/// a 401 before giving up — the same contract as the web client (web/src/lib/api.ts).
///
/// An `actor` so token reads/writes and the single-flight refresh are serialized.
actor APIClient {
    static let shared = APIClient()

    private let base = Config.apiBaseURL
    private let session = URLSession(configuration: .default)

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    private let accessKey = "access"
    private let refreshKey = "refresh"

    // MARK: - Token storage

    var hasSession: Bool { Keychain.get(accessKey) != nil }

    private var accessToken: String? { Keychain.get(accessKey) }
    private var refreshToken: String? { Keychain.get(refreshKey) }

    private func store(_ pair: TokenPair) {
        Keychain.set(pair.accessToken, for: accessKey)
        Keychain.set(pair.refreshToken, for: refreshKey)
    }

    func clearTokens() {
        Keychain.set(nil, for: accessKey)
        Keychain.set(nil, for: refreshKey)
    }

    // MARK: - Public API

    @discardableResult
    func login(username: String, password: String, totpCode: String? = nil) async throws -> TokenPair {
        let body = LoginRequest(username: username, password: password, totpCode: totpCode)
        let pair: TokenPair = try await requestJSON("/auth/login", method: "POST",
                                                     bodyData: try encoder.encode(body), authed: false)
        store(pair)
        return pair
    }

    func logout() async {
        _ = try? await requestData("/auth/logout", method: "POST", bodyData: nil, authed: true)
        clearTokens()
    }

    func me() async throws -> UserOut {
        try await requestJSON("/auth/me", method: "GET", bodyData: nil, authed: true)
    }

    // MARK: - Profile & security

    func profile() async throws -> UserOut {
        try await requestJSON("/profile", method: "GET", bodyData: nil, authed: true)
    }

    @discardableResult
    func updateProfile(_ body: ProfileUpdate) async throws -> UserOut {
        try await requestJSON("/profile", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }

    func changePassword(_ body: PasswordChangeInput) async throws {
        _ = try await requestData("/auth/change-password", method: "POST",
                                  bodyData: try encoder.encode(body), authed: true)
    }

    func twoFAStatus() async throws -> TwoFAStatus {
        try await requestJSON("/profile/2fa", method: "GET", bodyData: nil, authed: true)
    }

    func twoFASetup() async throws -> TwoFASetupResponse {
        try await requestJSON("/profile/2fa/setup", method: "POST", bodyData: nil, authed: true)
    }

    func twoFAVerify(_ body: TwoFAVerifyInput) async throws {
        _ = try await requestData("/profile/2fa/verify", method: "POST",
                                  bodyData: try encoder.encode(body), authed: true)
    }

    func twoFADisable() async throws {
        _ = try await requestData("/profile/2fa/disable", method: "POST", bodyData: nil, authed: true)
    }

    func dashboardStats() async throws -> DashboardStats {
        try await requestJSON("/dashboard/stats", method: "GET", bodyData: nil, authed: true)
    }

    func recruits(search: String? = nil, stage: RecruitStage? = nil,
                  skip: Int = 0, limit: Int = 100) async throws -> Page<RecruitOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let stage { q.append(URLQueryItem(name: "stage", value: stage.rawValue)) }
        return try await requestJSON("/recruits", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func recruit(id: Int) async throws -> RecruitOut {
        try await requestJSON("/recruits/\(id)", method: "GET", bodyData: nil, authed: true)
    }

    /// A recruit's stage transitions, newest first as returned by the backend.
    func recruitStageHistory(id: Int) async throws -> [StageEvent] {
        try await requestJSON("/recruits/\(id)/stage-history", method: "GET", bodyData: nil, authed: true)
    }

    func cadets(search: String? = nil, status: String? = nil,
                skip: Int = 0, limit: Int = 100) async throws -> Page<CadetOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let status, !status.isEmpty { q.append(URLQueryItem(name: "status", value: status)) }
        return try await requestJSON("/cadets", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func cadet(id: Int) async throws -> CadetOut {
        try await requestJSON("/cadets/\(id)", method: "GET", bodyData: nil, authed: true)
    }

    func contacts(search: String? = nil, isActive: Bool? = nil,
                  skip: Int = 0, limit: Int = 200) async throws -> Page<ContactOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let isActive { q.append(URLQueryItem(name: "is_active", value: isActive ? "true" : "false")) }
        return try await requestJSON("/contacts", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func contact(id: Int) async throws -> ContactOut {
        try await requestJSON("/contacts/\(id)", method: "GET", bodyData: nil, authed: true)
    }

    func events(search: String? = nil, status: String? = nil, eventType: String? = nil,
                skip: Int = 0, limit: Int = 200) async throws -> Page<EventOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let status, !status.isEmpty { q.append(URLQueryItem(name: "status", value: status)) }
        if let eventType, !eventType.isEmpty { q.append(URLQueryItem(name: "event_type", value: eventType)) }
        return try await requestJSON("/events", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func event(id: Int) async throws -> EventOut {
        try await requestJSON("/events/\(id)", method: "GET", bodyData: nil, authed: true)
    }

    func followups(assigneeId: String? = nil, status: String? = nil, dueBefore: String? = nil,
                   skip: Int = 0, limit: Int = 200) async throws -> Page<FollowUpOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let assigneeId, !assigneeId.isEmpty { q.append(URLQueryItem(name: "assignee_id", value: assigneeId)) }
        if let status, !status.isEmpty { q.append(URLQueryItem(name: "status", value: status)) }
        if let dueBefore, !dueBefore.isEmpty { q.append(URLQueryItem(name: "due_before", value: dueBefore)) }
        return try await requestJSON("/followups", method: "GET", bodyData: nil, authed: true, query: q)
    }

    /// Mark a follow-up done. Returns the updated row.
    @discardableResult
    func completeFollowup(id: Int) async throws -> FollowUpOut {
        try await requestJSON("/followups/\(id)/complete", method: "POST", bodyData: nil, authed: true)
    }

    func analyticsFunnel() async throws -> FunnelResponse {
        try await requestJSON("/analytics/funnel", method: "GET", bodyData: nil, authed: true)
    }

    func analyticsTrends(interval: String = "week") async throws -> TrendsResponse {
        let q = [URLQueryItem(name: "metric", value: "all"),
                 URLQueryItem(name: "interval", value: interval)]
        return try await requestJSON("/analytics/trends", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func materialLinks(search: String? = nil, category: String? = nil,
                       skip: Int = 0, limit: Int = 200) async throws -> Page<LinkOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let category, !category.isEmpty { q.append(URLQueryItem(name: "category", value: category)) }
        return try await requestJSON("/materials/links", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func materialDocuments(search: String? = nil, category: String? = nil,
                           skip: Int = 0, limit: Int = 200) async throws -> Page<DocumentOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let category, !category.isEmpty { q.append(URLQueryItem(name: "category", value: category)) }
        return try await requestJSON("/materials/documents", method: "GET", bodyData: nil, authed: true, query: q)
    }

    /// Download a document's raw bytes (authenticated). The caller pairs this with
    /// the document's `originalFilename` to save/share it.
    func downloadDocument(id: Int) async throws -> Data {
        try await requestData("/materials/documents/\(id)/download", method: "GET",
                              bodyData: nil, authed: true)
    }

    // MARK: - Mutations

    // Recruits
    @discardableResult
    func createRecruit(_ body: RecruitCreateInput) async throws -> RecruitOut {
        try await requestJSON("/recruits", method: "POST", bodyData: try encoder.encode(body), authed: true)
    }
    @discardableResult
    func updateRecruit(id: Int, _ body: RecruitUpdateInput) async throws -> RecruitOut {
        try await requestJSON("/recruits/\(id)", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }
    func deleteRecruit(id: Int) async throws {
        _ = try await requestData("/recruits/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }
    @discardableResult
    func changeRecruitStage(id: Int, toStage: String, note: String? = nil) async throws -> RecruitOut {
        let body = StageChangeInput(toStage: toStage, note: note)
        return try await requestJSON("/recruits/\(id)/stage", method: "POST",
                                     bodyData: try encoder.encode(body), authed: true)
    }

    // Cadets
    @discardableResult
    func createCadet(_ body: CadetCreateInput) async throws -> CadetOut {
        try await requestJSON("/cadets", method: "POST", bodyData: try encoder.encode(body), authed: true)
    }
    @discardableResult
    func updateCadet(id: Int, _ body: CadetUpdateInput) async throws -> CadetOut {
        try await requestJSON("/cadets/\(id)", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }
    func deleteCadet(id: Int) async throws {
        _ = try await requestData("/cadets/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    // Contacts
    @discardableResult
    func createContact(_ body: ContactCreateInput) async throws -> ContactOut {
        try await requestJSON("/contacts", method: "POST", bodyData: try encoder.encode(body), authed: true)
    }
    @discardableResult
    func updateContact(id: Int, _ body: ContactUpdateInput) async throws -> ContactOut {
        try await requestJSON("/contacts/\(id)", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }
    func deleteContact(id: Int) async throws {
        _ = try await requestData("/contacts/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    // Events
    @discardableResult
    func createEvent(_ body: EventCreateInput) async throws -> EventOut {
        try await requestJSON("/events", method: "POST", bodyData: try encoder.encode(body), authed: true)
    }
    @discardableResult
    func updateEvent(id: Int, _ body: EventUpdateInput) async throws -> EventOut {
        try await requestJSON("/events/\(id)", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }
    func deleteEvent(id: Int) async throws {
        _ = try await requestData("/events/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    // Follow-ups
    @discardableResult
    func createFollowup(_ body: FollowUpCreateInput) async throws -> FollowUpOut {
        try await requestJSON("/followups", method: "POST", bodyData: try encoder.encode(body), authed: true)
    }
    @discardableResult
    func updateFollowup(id: Int, _ body: FollowUpUpdateInput) async throws -> FollowUpOut {
        try await requestJSON("/followups/\(id)", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }
    func deleteFollowup(id: Int) async throws {
        _ = try await requestData("/followups/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    // MARK: - Core request

    private func requestJSON<T: Decodable>(_ path: String, method: String, bodyData: Data?,
                                           authed: Bool, query: [URLQueryItem] = []) async throws -> T {
        let data = try await requestData(path, method: method, bodyData: bodyData, authed: authed, query: query)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(String(describing: error))
        }
    }

    @discardableResult
    private func requestData(_ path: String, method: String, bodyData: Data?,
                             authed: Bool, query: [URLQueryItem] = [],
                             retry: Bool = true) async throws -> Data {
        guard var comps = URLComponents(string: base.absoluteString + path) else {
            throw APIError.invalidResponse
        }
        if !query.isEmpty { comps.queryItems = query }
        guard let url = comps.url else { throw APIError.invalidResponse }

        var req = URLRequest(url: url)
        req.httpMethod = method
        if let bodyData {
            req.httpBody = bodyData
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if authed, let token = accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let data: Data, response: URLResponse
        do {
            (data, response) = try await session.data(for: req)
        } catch {
            throw APIError.transport(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }

        if http.statusCode == 401 && authed && retry, await refreshTokens() {
            return try await requestData(path, method: method, bodyData: bodyData,
                                         authed: authed, query: query, retry: false)
        }

        guard (200..<300).contains(http.statusCode) else {
            if http.statusCode == 401 { throw APIError.unauthorized }
            throw APIError.http(status: http.statusCode, message: Self.messageFromDetail(data))
        }
        return data
    }

    private func refreshTokens() async -> Bool {
        guard let refresh = refreshToken else { return false }
        do {
            let body = try encoder.encode(RefreshRequest(refreshToken: refresh))
            let data = try await requestData("/auth/refresh", method: "POST",
                                             bodyData: body, authed: false, retry: false)
            let pair = try decoder.decode(TokenPair.self, from: data)
            store(pair)
            return true
        } catch {
            clearTokens()
            return false
        }
    }

    /// Pull a human message out of a FastAPI error body: `{"detail": "..."}` or
    /// `{"detail": [{"msg": "..."}]}`.
    private static func messageFromDetail(_ data: Data) -> String {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return "" }
        if let s = obj["detail"] as? String { return s }
        if let arr = obj["detail"] as? [[String: Any]], let first = arr.first,
           let msg = first["msg"] as? String { return msg }
        return ""
    }
}
