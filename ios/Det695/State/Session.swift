import Foundation

/// Observable auth state for the view tree. Owns login/logout and the current
/// user; `RootView` switches on `isAuthenticated`.
@MainActor
final class Session: ObservableObject {
    enum Phase { case loading, signedOut, signedIn }

    @Published private(set) var phase: Phase = .loading
    @Published private(set) var user: UserOut?
    @Published var loginError: String?
    @Published var isSubmitting = false

    var isAuthenticated: Bool { phase == .signedIn }

    init() {
        Task { await restore() }
    }

    /// On launch, if we hold a token, try to fetch the current user to confirm
    /// the session is still valid; otherwise land on the login screen.
    func restore() async {
        #if DEBUG
        // Test affordance: `DET695_AUTOLOGIN=1` signs in on launch so the
        // authenticated screens can be smoke-tested from the CLI (the Simulator
        // has no scriptable text entry). Inert unless the env var is set.
        let env = ProcessInfo.processInfo.environment
        if env["DET695_AUTOLOGIN"] == "1" {
            await login(username: env["DET695_AUTOLOGIN_USER"] ?? "admin",
                        password: env["DET695_AUTOLOGIN_PASS"] ?? "Det695Demo!",
                        totpCode: nil)
            return
        }
        #endif
        guard await APIClient.shared.hasSession else {
            phase = .signedOut
            return
        }
        do {
            user = try await APIClient.shared.me()
            phase = .signedIn
        } catch {
            await APIClient.shared.clearTokens()
            phase = .signedOut
        }
    }

    func login(username: String, password: String, totpCode: String?) async {
        loginError = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            _ = try await APIClient.shared.login(username: username, password: password,
                                                 totpCode: totpCode?.isEmpty == true ? nil : totpCode)
            user = try await APIClient.shared.me()
            phase = .signedIn
        } catch {
            loginError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func logout() async {
        await APIClient.shared.logout()
        user = nil
        phase = .signedOut
    }
}
