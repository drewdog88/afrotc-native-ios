import Foundation

/// Observable auth state for the view tree. Owns login/logout and the current
/// user; `RootView` switches on `isAuthenticated`.
@MainActor
final class Session: ObservableObject {
    enum Phase { case loading, signedOut, signedIn }

    /// An in-flight 2FA login challenge — set when `login` returns a challenge
    /// instead of tokens. `Identifiable` so `LoginView` can drive a
    /// `.sheet(item:)` off it; cleared on successful verify or cancel.
    struct LoginChallenge: Identifiable {
        let id = UUID()
        let token: String
        let method: String
    }

    @Published private(set) var phase: Phase = .loading
    @Published private(set) var user: UserOut?
    @Published var loginError: String?
    @Published var isSubmitting = false
    @Published var challenge: LoginChallenge?

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
        if env["DET695_AUTOLOGIN"] == "1", let pass = env["DET695_AUTOLOGIN_PASS"] {
            await login(username: env["DET695_AUTOLOGIN_USER"] ?? "admin",
                        password: pass)
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

    /// Step 1 — submit credentials. On a 2FA challenge, publish `challenge`
    /// (LoginView presents the verify sheet); otherwise complete the sign-in.
    func login(username: String, password: String) async {
        loginError = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            let outcome = try await APIClient.shared.login(username: username, password: password)
            switch outcome {
            case .authenticated:
                user = try await APIClient.shared.me()
                phase = .signedIn
            case let .challenge(token, method):
                challenge = LoginChallenge(token: token, method: method)
            }
        } catch {
            loginError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    /// Step 2 — submit the emailed code for the active challenge. Completes the
    /// sign-in and clears `challenge` (which dismisses the verify sheet).
    func verify(code: String, trustDevice: Bool) async {
        guard let challenge else { return }
        loginError = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            try await APIClient.shared.loginVerify(
                challengeToken: challenge.token, code: code, trustDevice: trustDevice
            )
            user = try await APIClient.shared.me()
            self.challenge = nil
            phase = .signedIn
        } catch {
            loginError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    /// Re-send the emailed code for the active challenge. Returns whether the
    /// send succeeded so the caller only starts its resend cooldown on success
    /// (a failure — e.g. hitting the resend cap — surfaces via `loginError`).
    @discardableResult
    func resend() async -> Bool {
        guard let challenge else { return false }
        do {
            try await APIClient.shared.loginResend(challengeToken: challenge.token)
            return true
        } catch {
            loginError = (error as? APIError)?.errorDescription ?? error.localizedDescription
            return false
        }
    }

    /// Replace the cached user after a self-service profile edit so any screen
    /// bound to `session.user` reflects the change immediately.
    func applyUpdatedUser(_ updated: UserOut) {
        user = updated
    }

    func logout() async {
        await APIClient.shared.logout()
        user = nil
        phase = .signedOut
    }
}
