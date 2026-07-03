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

    func cadets(search: String? = nil, status: String? = nil,
                skip: Int = 0, limit: Int = 100) async throws -> Page<CadetOut> {
        var q = [URLQueryItem(name: "skip", value: String(skip)),
                 URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { q.append(URLQueryItem(name: "search", value: search)) }
        if let status, !status.isEmpty { q.append(URLQueryItem(name: "status", value: status)) }
        return try await requestJSON("/cadets", method: "GET", bodyData: nil, authed: true, query: q)
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
