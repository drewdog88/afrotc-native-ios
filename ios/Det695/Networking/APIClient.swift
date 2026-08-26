import Foundation

/// Structured tracing for the network layer, compiled out of release builds.
/// View it live in DEBUG with:
///   xcrun simctl spawn booted log stream \
///     --predicate 'subsystem == "com.det695.recruiting" && category == "net"'
/// (drop `simctl spawn booted` and use Console.app / `log stream` for a device).
private let netLog = DebugLog(category: "net")

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

    /// Trusted-device token — a long-lived opaque credential that lets a
    /// recognized device skip the 2FA challenge on future logins.
    func storedTrustToken() -> String? { Keychain.get("trust") }
    func setTrustToken(_ t: String) { Keychain.set(t, for: "trust") }

    // MARK: - Public API

    /// Step 1 of login. Returns `.authenticated` immediately when no 2FA
    /// challenge is required (or the attached trust token satisfies it),
    /// otherwise `.challenge` — the caller then calls `loginVerify`.
    @discardableResult
    func login(username: String, password: String) async throws -> LoginOutcome {
        let body = LoginRequest(username: username, password: password, totpCode: nil,
                                 trustToken: storedTrustToken())
        let resp: LoginResponse = try await requestJSON(
            "/auth/login", method: "POST", bodyData: try encoder.encode(body), authed: false
        )
        if resp.twoFactorRequired {
            return .challenge(token: resp.challengeToken ?? "", method: resp.method ?? "email")
        }
        let pair = TokenPair(
            accessToken: resp.accessToken ?? "",
            refreshToken: resp.refreshToken ?? "",
            forcePasswordChange: resp.forcePasswordChange,
            tokenType: resp.tokenType
        )
        store(pair)
        return .authenticated(pair)
    }

    /// Step 2 of login — submit the emailed code for the challenge issued by
    /// `login`. On success, stores the token pair and (if the device was
    /// marked trusted) the new trust token.
    func loginVerify(challengeToken: String, code: String, trustDevice: Bool) async throws {
        let body = LoginVerifyInput(challengeToken: challengeToken, code: code, trustDevice: trustDevice)
        let resp: LoginVerifyResponse = try await requestJSON(
            "/auth/login/verify", method: "POST", bodyData: try encoder.encode(body), authed: false
        )
        store(TokenPair(
            accessToken: resp.accessToken, refreshToken: resp.refreshToken,
            forcePasswordChange: resp.forcePasswordChange, tokenType: resp.tokenType
        ))
        if let t = resp.trustToken { setTrustToken(t) }
    }

    /// Re-send the 2FA code for an in-flight login challenge.
    func loginResend(challengeToken: String) async throws {
        _ = try await requestData(
            "/auth/login/resend", method: "POST",
            bodyData: try encoder.encode(ResendInput(challengeToken: challengeToken)), authed: false
        )
    }

    func logout() async {
        _ = try? await requestData("/auth/logout", method: "POST", bodyData: nil, authed: true)
        clearTokens()
    }

    func me() async throws -> UserOut {
        try await requestJSON("/auth/me", method: "GET", bodyData: nil, authed: true)
    }

    /// Step 1 of self-service reset — returns the account's security question.
    func forgotPassword(username: String) async throws -> SecretQuestionOut {
        let body = ForgotPasswordRequest(username: username)
        return try await requestJSON("/auth/forgot-password", method: "POST",
                                     bodyData: try encoder.encode(body), authed: false)
    }

    /// Step 2 — answer the question and set a new password (also clears lockout).
    @discardableResult
    func resetPassword(username: String, secretAnswer: String, newPassword: String) async throws -> UserOut {
        let body = ResetPasswordRequest(username: username, secretAnswer: secretAnswer, newPassword: newPassword)
        return try await requestJSON("/auth/reset-password", method: "POST",
                                     bodyData: try encoder.encode(body), authed: false)
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
        try await requestJSON("/profile/2fa/status", method: "GET", bodyData: nil, authed: true)
    }

    /// Begin email-2FA enrollment.
    func enroll() async throws {
        _ = try await requestData("/profile/2fa/enroll", method: "POST",
                                  bodyData: try encoder.encode(TwoFAEnrollInput(method: "email")), authed: true)
    }

    /// Confirm enrollment with the emailed code.
    func enrollVerify(code: String) async throws {
        _ = try await requestData("/profile/2fa/enroll/verify", method: "POST",
                                  bodyData: try encoder.encode(TwoFAEnrollVerifyInput(code: code)), authed: true)
    }

    /// Dismiss the enrollment nudge without enabling 2FA.
    func enrollmentDismiss() async throws {
        _ = try await requestData("/profile/2fa/enrollment-dismiss", method: "POST", bodyData: nil, authed: true)
    }

    func disable2FA() async throws {
        _ = try await requestData("/profile/2fa/disable", method: "POST", bodyData: nil, authed: true)
    }

    func listTrustedDevices() async throws -> [TrustedDevice] {
        try await requestJSON("/profile/trusted-devices", method: "GET", bodyData: nil, authed: true)
    }

    func revokeTrustedDevice(id: Int) async throws {
        _ = try await requestData("/profile/trusted-devices/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    /// Revoke every trusted device except the one currently in use (identified
    /// by the trust token this client is carrying, if any).
    func revokeOtherTrustedDevices() async throws {
        struct Body: Encodable { let trustToken: String? }
        _ = try await requestData("/profile/trusted-devices/revoke-others", method: "POST",
                                  bodyData: try encoder.encode(Body(trustToken: storedTrustToken())), authed: true)
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

    // Material links
    @discardableResult
    func createLink(_ body: LinkCreateInput) async throws -> LinkOut {
        try await requestJSON("/materials/links", method: "POST",
                              bodyData: try encoder.encode(body), authed: true)
    }
    @discardableResult
    func updateLink(id: Int, _ body: LinkUpdateInput) async throws -> LinkOut {
        try await requestJSON("/materials/links/\(id)", method: "PATCH",
                              bodyData: try encoder.encode(body), authed: true)
    }
    func deleteLink(id: Int) async throws {
        _ = try await requestData("/materials/links/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    // Documents
    /// Upload a document as multipart/form-data. Title/description/category ride
    /// as query params (the backend reads them as query args, not form fields).
    @discardableResult
    func uploadDocument(fileData: Data, filename: String, mimeType: String,
                        title: String? = nil, description: String? = nil,
                        category: String? = nil) async throws -> DocumentOut {
        var q: [URLQueryItem] = []
        if let title, !title.isEmpty { q.append(URLQueryItem(name: "title", value: title)) }
        if let description, !description.isEmpty { q.append(URLQueryItem(name: "description", value: description)) }
        if let category, !category.isEmpty { q.append(URLQueryItem(name: "category", value: category)) }

        let boundary = "Boundary-\(UUID().uuidString)"
        var body = Data()
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n")
        body.append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n")

        return try await requestJSON("/materials/documents", method: "POST", bodyData: body,
                                     authed: true, query: q,
                                     contentType: "multipart/form-data; boundary=\(boundary)")
    }
    func deleteDocument(id: Int) async throws {
        _ = try await requestData("/materials/documents/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    // MARK: - Bulk import

    /// Upload a CSV/Excel roster to `/recruits/import` as multipart/form-data and
    /// get back the per-row result. Write-gated on the backend (`require_write`).
    func importRecruits(fileData: Data, filename: String, mimeType: String) async throws -> ImportResult {
        let boundary = "Boundary-\(UUID().uuidString)"
        var body = Data()
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n")
        body.append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n")
        return try await requestJSON("/recruits/import", method: "POST", bodyData: body,
                                     authed: true,
                                     contentType: "multipart/form-data; boundary=\(boundary)")
    }

    // MARK: - Admin

    func adminUsers(search: String? = nil, skip: Int = 0, limit: Int = 200) async throws -> Page<UserOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        return try await requestJSON("/admin/users", method: "GET", bodyData: nil, authed: true, query: q)
    }

    @discardableResult
    func createAdminUser(_ body: AdminUserCreate) async throws -> UserOut {
        try await requestJSON("/admin/users", method: "POST", bodyData: try encoder.encode(body), authed: true)
    }

    @discardableResult
    func updateAdminUser(id: Int, _ body: AdminUserUpdate) async throws -> UserOut {
        try await requestJSON("/admin/users/\(id)", method: "PATCH", bodyData: try encoder.encode(body), authed: true)
    }

    func deleteAdminUser(id: Int) async throws {
        _ = try await requestData("/admin/users/\(id)", method: "DELETE", bodyData: nil, authed: true)
    }

    /// Admin action — revoke all of a user's trusted devices (e.g. after a
    /// suspected compromise), forcing 2FA on their next login.
    func adminRevokeTrustedDevices(userId: Int) async throws {
        _ = try await requestData("/admin/users/\(userId)/revoke-trusted-devices", method: "POST",
                                  bodyData: nil, authed: true)
    }

    func adminActivity(skip: Int = 0, limit: Int = 25) async throws -> Page<ActivityLogOut> {
        let q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        return try await requestJSON("/admin/activity", method: "GET", bodyData: nil, authed: true, query: q)
    }

    func intakeSettings() async throws -> IntakeSettingsOut {
        try await requestJSON("/admin/intake-settings", method: "GET", bodyData: nil, authed: true)
    }

    @discardableResult
    func updateIntakeSettings(_ body: IntakeSettingsUpdate) async throws -> IntakeSettingsOut {
        try await requestJSON("/admin/intake-settings", method: "PUT",
                              bodyData: try encoder.encode(body), authed: true)
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
                                           authed: Bool, query: [URLQueryItem] = [],
                                           contentType: String = "application/json") async throws -> T {
        let data = try await requestData(path, method: method, bodyData: bodyData, authed: authed,
                                         query: query, contentType: contentType)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            let snippet = String(decoding: data.prefix(512), as: UTF8.self)
            netLog.error("✗ decode \(T.self) failed for \(path): \(String(describing: error)) — body=\(snippet)")
            throw APIError.decoding(String(describing: error))
        }
    }

    @discardableResult
    private func requestData(_ path: String, method: String, bodyData: Data?,
                             authed: Bool, query: [URLQueryItem] = [],
                             contentType: String = "application/json",
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
            req.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        if authed, let token = accessToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        netLog.notice("→ \(method) \(url.absoluteString) authed=\(authed) bodyBytes=\(bodyData?.count ?? 0)")

        let data: Data, response: URLResponse
        do {
            (data, response) = try await session.data(for: req)
        } catch {
            let ns = error as NSError
            netLog.error("✗ transport \(method) \(url.absoluteString): \(ns.domain) code=\(ns.code) \(ns.localizedDescription)")
            throw APIError.transport(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            netLog.error("✗ non-HTTP response for \(url.absoluteString)")
            throw APIError.invalidResponse
        }

        // The final URL after any redirects, plus Vercel's mitigation marker, so a
        // security-checkpoint challenge (HTML body on a 2xx/redirect) is obvious in the log.
        let finalURL = http.url?.absoluteString ?? url.absoluteString
        let mitigated = http.value(forHTTPHeaderField: "x-vercel-mitigated") ?? "-"
        netLog.notice("← \(http.statusCode) \(finalURL) bytes=\(data.count) vercel-mitigated=\(mitigated)")

        if http.statusCode == 401 && authed && retry, await refreshTokens() {
            return try await requestData(path, method: method, bodyData: bodyData,
                                         authed: authed, query: query,
                                         contentType: contentType, retry: false)
        }

        guard (200..<300).contains(http.statusCode) else {
            let bodySnippet = String(decoding: data.prefix(512), as: UTF8.self)
            netLog.error("✗ \(http.statusCode) \(finalURL) body=\(bodySnippet)")
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
            // The backend returns an access-only token — the refresh token is
            // not rotated — so only the access Keychain entry is updated here.
            // Calling `store(...)` would overwrite (wipe) the still-valid
            // refresh token with an empty one.
            let token = try decoder.decode(AccessToken.self, from: data)
            Keychain.set(token.accessToken, for: accessKey)
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

private extension Data {
    /// Append a UTF-8 string — used to assemble multipart/form-data bodies.
    mutating func append(_ string: String) {
        if let d = string.data(using: .utf8) { append(d) }
    }
}
