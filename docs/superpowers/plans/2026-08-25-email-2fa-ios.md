# Email-2FA iOS Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the shipped email-2FA backend into the Det695 SwiftUI app — a login verify sheet, first-login enrollment sheet, Profile email-2FA + trusted-device management, and an admin 2FA toggle — so 2FA works end-to-end on iOS.

**Architecture:** SwiftUI (iOS 17), `APIClient` actor singleton with a generic `requestJSON`/`requestData` core and global snake_case↔camelCase JSON coding. Tokens live in Keychain (accounts `access`/`refresh`). `Session` (`@MainActor ObservableObject`) drives a `Phase { loading, signedOut, signedIn }` root switch in `RootView`. The 2FA login flow becomes two-step: `APIClient.login` returns a sum type (`LoginOutcome`) that is either a `TokenPair` or a challenge; on a challenge `Session` publishes a `challenge`, `LoginView` presents a `TwoFactorVerifyView` sheet, and verification calls `/auth/login/verify`. The trusted-device `trust_token` is stored in Keychain (account `trust`) and sent in the login **body**.

**Tech Stack:** Swift 5 / SwiftUI, URLSession, XcodeGen (`project.yml` → `Det695.xcodeproj`). No test target exists.

**Spec:** `docs/superpowers/specs/2026-08-25-email-2fa-design.md` ("Clients → iOS" section + the API contract). Read it alongside this plan.

## Global Constraints

- **JSON coding is global:** the shared decoder/encoder use `.convertFromSnakeCase`/`.convertToSnakeCase` (APIClient lines ~21-30). Declare Swift properties in camelCase; **no hand-written `CodingKeys`**. Backend `two_factor_required` → `twoFactorRequired`, etc.
- **Decode-resilience:** new fields on existing response models (`UserOut`) MUST be defaulted `var`s (follow `isLocked: Bool = false`, Auth.swift ~line 35) so older/partial `/auth/me` payloads still decode.
- **Trust-token transport (RULING):** store the trusted-device token in Keychain under account `"trust"` (same `Keychain` API as tokens). Send it as `trustToken` in the `/auth/login` body (serialized to `trust_token`). After a successful verify with "trust this device", write the returned `trust_token`. Do **not** clear it on sign-out; clear it only when the user revokes the current device / disables 2FA locally is not required. The backend cookie is irrelevant on iOS.
- **Login is now a sum type (RULING):** `APIClient.login` returns `LoginOutcome` (`.authenticated(TokenPair)` | `.challenge(token:method:)`); it must NOT force-decode a `TokenPair` (a challenge response has no tokens and would throw `.decoding`). Only `.authenticated` calls `store(...)`.
- **Code policy (display only; backend enforces):** 6-digit numeric, 10-min expiry, max 5 verify attempts, 60s resend cooldown, max 3 resends. Surface countdown/attempt errors from the backend; never enforce client-side as the source of truth.
- **Verify UI placement:** `LoginView` has **no `NavigationStack`**, so the verify step is a `.sheet` (model it on `ForgotPasswordView`'s single-sheet, internal-`enum Step` state machine).
- **2FA model/struct location:** new request/response Codable types live in `Models/Profile.swift` and `Models/Auth.swift` (matching the existing 2FA structs), NOT `Networking/Inputs.swift`.
- **State pattern:** views are structs with `@State` + `Task {}` async funcs; the only `ObservableObject` is `Session`. Errors shown inline via `(error as? APIError)?.errorDescription ?? error.localizedDescription`; loading via `ProgressView()`/local bools; the `StatusLine` helper (ProfileView ~316-329) for inline success/failure.
- **VERIFICATION (RULING — no unit tests):** there is no XCTest target and no reliable simulator in this environment. Each task is verified by regenerating the project and compiling:
  `cd ios && xcodegen generate && xcodebuild -project Det695.xcodeproj -scheme Det695 -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' build CODE_SIGNING_ALLOWED=NO -quiet`
  A clean build = the task's type-level contract holds. If `xcodebuild` cannot run in the execution environment, the implementer MUST say so explicitly in its report and fall back to a careful self-review of the diff against this plan — it must never claim a build passed that it did not run. Manual UI smoke is documented in Final Verification.

---

## File Structure

- `ios/Det695/Models/Auth.swift` — `LoginRequest.trustToken`; `LoginResponse`; `LoginOutcome`; `LoginVerifyInput`/`LoginVerifyResponse`; `ResendInput`; `UserOut` 2FA fields.
- `ios/Det695/Models/Profile.swift` — replace TOTP `TwoFAStatus`/`TwoFASetupResponse`/`TwoFAVerifyInput` with email-2FA `TwoFAStatus`, `TwoFAEnrollInput`, `TwoFAEnrollVerifyInput`; add `TrustedDevice`.
- `ios/Det695/Models/Admin.swift` — `AdminUserUpdate.twoFactorEnabled`.
- `ios/Det695/Networking/APIClient.swift` — sum-type `login`; `loginVerify`/`loginResend`/`enroll`/`enrollVerify`/`enrollmentDismiss`/`disable2FA`/`listTrustedDevices`/`revokeTrustedDevice`/`revokeOtherTrustedDevices`/`adminRevokeTrustedDevices`; read/attach trust token.
- `ios/Det695/State/Session.swift` — `challenge` state + `verify`/`resend`; store trust token.
- `ios/Det695/Views/LoginView.swift` — remove TOTP field; present verify sheet on challenge.
- `ios/Det695/Views/TwoFactorVerifyView.swift` (new) — code entry + resend + trust toggle.
- `ios/Det695/Views/EnrollmentSheet.swift` (new) + `RootView.swift` — one-time enrollment sheet.
- `ios/Det695/Views/ProfileView.swift` — replace `TwoFactorSection` with email-2FA + Trusted Devices.
- `ios/Det695/Views/AdminView.swift` — 2FA toggle + revoke trusted devices.

---

### Task 1: Models — login sum type, trust token, 2FA fields

**Files:**
- Modify: `ios/Det695/Models/Auth.swift`
- Modify: `ios/Det695/Models/Profile.swift`
- Modify: `ios/Det695/Models/Admin.swift`

**Interfaces:**
- Produces (consumed by every later task):
  - `LoginRequest` gains `var trustToken: String?`.
  - `LoginResponse` (Decodable): optional tokens + `twoFactorRequired`/`method`/`challengeToken`.
  - `LoginOutcome` (enum): `.authenticated(TokenPair)` | `.challenge(token: String, method: String)`.
  - `LoginVerifyInput{challengeToken, code, trustDevice}`; `LoginVerifyResponse` (TokenPair fields + `trustToken?`); `ResendInput{challengeToken}`.
  - `UserOut` gains `var twoFactorEnabled = false`, `var twoFactorMethod: String?`, `var twoFactorEnrollmentPrompted = false`, `var is2faActive = false` (defaulted).
  - `TwoFAStatus{enabled, method, enrollmentPrompted}`; `TwoFAEnrollInput{method}`; `TwoFAEnrollVerifyInput{code}`; `TrustedDevice{id, deviceLabel, createdAt, lastUsedAt, expiresAt}` (Decodable, Identifiable).
  - `AdminUserUpdate` gains `var twoFactorEnabled: Bool?`.

- [ ] **Step 1: Auth.swift**

```swift
struct LoginRequest: Encodable {
    let username: String
    let password: String
    let totpCode: String?          // legacy; leave for compat, always nil now
    var trustToken: String? = nil
}

struct LoginResponse: Decodable {
    let accessToken: String?
    let refreshToken: String?
    var tokenType: String = "bearer"
    var forcePasswordChange: Bool = false
    var twoFactorRequired: Bool = false
    var method: String?
    var challengeToken: String?
}

enum LoginOutcome {
    case authenticated(TokenPair)
    case challenge(token: String, method: String)
}

struct LoginVerifyInput: Encodable {
    let challengeToken: String
    let code: String
    let trustDevice: Bool
}

struct LoginVerifyResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    var tokenType: String = "bearer"
    var forcePasswordChange: Bool = false
    var trustToken: String?
}

struct ResendInput: Encodable { let challengeToken: String }
```

Add to `UserOut` (defaulted `var`s, mirroring `isLocked`):
```swift
    var twoFactorEnabled: Bool = false
    var twoFactorMethod: String? = nil
    var twoFactorEnrollmentPrompted: Bool = false
    var is2faActive: Bool = false
```

- [ ] **Step 2: Profile.swift** — replace the TOTP structs:

```swift
struct TwoFAStatus: Decodable {
    var enabled: Bool = false
    var method: String? = nil
    var enrollmentPrompted: Bool = false
}
struct TwoFAEnrollInput: Encodable { let method: String }         // "email"
struct TwoFAEnrollVerifyInput: Encodable { let code: String }

struct TrustedDevice: Decodable, Identifiable {
    let id: Int
    let deviceLabel: String
    let createdAt: Date
    let lastUsedAt: Date
    let expiresAt: Date
}
```

Delete `TwoFASetupResponse` and the TOTP-shaped `TwoFAVerifyInput` (the ProfileView rewrite in Task 8 removes their last uses; if a transient compile error remains until then, note it — it is resolved by Task 8).

Note: `TrustedDevice` date decoding depends on the shared decoder's date strategy. Check APIClient's `JSONDecoder` `dateDecodingStrategy`; if dates elsewhere decode as ISO8601, this matches. If the decoder uses a custom strategy, keep these as `Date`; if there is NO date strategy configured, declare them as `String` instead and format for display. Verify against how `createdAt` is already decoded on other models before finalizing the type.

- [ ] **Step 3: Admin.swift** — add to `AdminUserUpdate`:
```swift
    var twoFactorEnabled: Bool? = nil
```

- [ ] **Step 4: Compile**

Run the build command from Global Constraints. Expected: compiles (uses of the deleted TOTP structs in `ProfileView`/`APIClient` may error — if so, they are fixed in Tasks 3 & 8; a build that fails ONLY on those known call sites is acceptable at this step; record which sites).

- [ ] **Step 5: Commit**

```bash
git add ios/Det695/Models/Auth.swift ios/Det695/Models/Profile.swift ios/Det695/Models/Admin.swift
git commit -m "feat(ios): 2FA models — login sum type, trust token, user + device fields"
```

---

### Task 2: Trust-token Keychain access

**Files:**
- Modify: `ios/Det695/Networking/APIClient.swift` (or a small extension where token helpers live)

**Interfaces:**
- Produces: within `APIClient`, `trustToken` read/write helpers using the existing `Keychain` API with account `"trust"`:
  - reading: `Keychain.get("trust")`
  - writing: `Keychain.set(token, for: "trust")`

No new file needed — the existing `Keychain` enum (Support/Keychain.swift) is a generic keyed store. This task only adds the small internal helpers/usages; it is folded into Task 3 if trivial, but kept explicit so the trust-token plumbing is reviewable.

- [ ] **Step 1: Add helpers** near the existing `store`/`clearTokens` in `APIClient`:
```swift
func storedTrustToken() -> String? { Keychain.get("trust") }
func setTrustToken(_ t: String) { Keychain.set(t, for: "trust") }
```

- [ ] **Step 2: Compile** (build command). Expected: PASS.

- [ ] **Step 3: Commit**
```bash
git add ios/Det695/Networking/APIClient.swift
git commit -m "feat(ios): Keychain trust-token accessors"
```

---

### Task 3: APIClient — two-step login + 2FA/device endpoints

**Files:**
- Modify: `ios/Det695/Networking/APIClient.swift`

**Interfaces:**
- Consumes: `LoginResponse`, `LoginOutcome`, `LoginVerifyInput/Response`, `ResendInput`, `TwoFAStatus`, `TwoFAEnrollInput`, `TwoFAEnrollVerifyInput`, `TrustedDevice`, `Keychain` trust helpers.
- Produces:
  - `login(username:password:) async throws -> LoginOutcome` — attaches `storedTrustToken()`, decodes `LoginResponse`, returns `.challenge` if `twoFactorRequired` else builds+stores a `TokenPair` and returns `.authenticated`.
  - `loginVerify(challengeToken:code:trustDevice:) async throws -> Void` — decodes `LoginVerifyResponse`, `store`s the pair, `setTrustToken` if present.
  - `loginResend(challengeToken:) async throws`
  - `enroll() async throws` (`{method:"email"}`), `enrollVerify(code:) async throws`, `enrollmentDismiss() async throws`, `disable2FA() async throws`
  - `twoFAStatus() async throws -> TwoFAStatus`
  - `listTrustedDevices() async throws -> [TrustedDevice]`, `revokeTrustedDevice(id:) async throws`, `revokeOtherTrustedDevices() async throws` (body `{trust_token: storedTrustToken()}`)
  - `adminRevokeTrustedDevices(userId:) async throws`

- [ ] **Step 1: Replace `login`**

```swift
@discardableResult
func login(username: String, password: String) async throws -> LoginOutcome {
    let body = LoginRequest(
        username: username, password: password, totpCode: nil,
        trustToken: storedTrustToken()
    )
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
```

(Match `TokenPair`'s memberwise init to its declaration in Auth.swift; adjust argument order/labels accordingly.)

- [ ] **Step 2: Add the verify/resend + profile/device/admin methods**, following the existing patterns (`requestJSON` for JSON-out, `requestData` for discard-response; `twoFASetup`/`updateProfile`/`updateAdminUser` are the templates). Examples:

```swift
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

func loginResend(challengeToken: String) async throws {
    _ = try await requestData(
        "/auth/login/resend", method: "POST",
        bodyData: try encoder.encode(ResendInput(challengeToken: challengeToken)), authed: false
    )
}

func twoFAStatus() async throws -> TwoFAStatus {
    try await requestJSON("/profile/2fa/status", method: "GET", authed: true)
}
func enroll() async throws {
    _ = try await requestData("/profile/2fa/enroll", method: "POST",
        bodyData: try encoder.encode(TwoFAEnrollInput(method: "email")), authed: true)
}
func enrollVerify(code: String) async throws {
    _ = try await requestData("/profile/2fa/enroll/verify", method: "POST",
        bodyData: try encoder.encode(TwoFAEnrollVerifyInput(code: code)), authed: true)
}
func enrollmentDismiss() async throws {
    _ = try await requestData("/profile/2fa/enrollment-dismiss", method: "POST", authed: true)
}
func disable2FA() async throws {
    _ = try await requestData("/profile/2fa/disable", method: "POST", authed: true)
}
func listTrustedDevices() async throws -> [TrustedDevice] {
    try await requestJSON("/profile/trusted-devices", method: "GET", authed: true)
}
func revokeTrustedDevice(id: Int) async throws {
    _ = try await requestData("/profile/trusted-devices/\(id)", method: "DELETE", authed: true)
}
func revokeOtherTrustedDevices() async throws {
    struct Body: Encodable { let trustToken: String? }
    _ = try await requestData("/profile/trusted-devices/revoke-others", method: "POST",
        bodyData: try encoder.encode(Body(trustToken: storedTrustToken())), authed: true)
}
func adminRevokeTrustedDevices(userId: Int) async throws {
    _ = try await requestData("/admin/users/\(userId)/revoke-trusted-devices", method: "POST", authed: true)
}
```

(Verify the exact `requestJSON`/`requestData` signatures — parameter labels for `method`, `bodyData`, `authed`, and whether GET needs no body — against the current APIClient before finalizing.)

- [ ] **Step 3: Compile** (build command). Expected: PASS (the `login` call sites in `Session` change in Task 4 — if the build fails ONLY at `Session.login`, that is expected and fixed next; record it).

- [ ] **Step 4: Commit**
```bash
git add ios/Det695/Networking/APIClient.swift
git commit -m "feat(ios): two-step login + 2FA/trusted-device API methods"
```

---

### Task 4: Session — challenge state + verify/resend

**Files:**
- Modify: `ios/Det695/State/Session.swift`

**Interfaces:**
- Consumes: `APIClient.login` (sum type), `loginVerify`, `loginResend`, `me`.
- Produces:
  - `struct LoginChallenge: Identifiable { let id = UUID(); let token: String; let method: String }`
  - `@Published var challenge: LoginChallenge?`
  - `login(...)` sets `challenge` on `.challenge`, or completes to `.signedIn` on `.authenticated`.
  - `verify(code:trustDevice:) async` → `loginVerify` → `me()` → `phase = .signedIn`, `challenge = nil`.
  - `resend() async` → `loginResend(challenge.token)`.

- [ ] **Step 1: Add the state and methods**

```swift
struct LoginChallenge: Identifiable {
    let id = UUID()
    let token: String
    let method: String
}

@Published var challenge: LoginChallenge?

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

func resend() async {
    guard let challenge else { return }
    do { try await APIClient.shared.loginResend(challengeToken: challenge.token) }
    catch { loginError = (error as? APIError)?.errorDescription ?? error.localizedDescription }
}
```

(Remove the old `totpCode` parameter from `login`. Update the existing `login` signature everywhere it is called — `LoginView` in Task 5.)

- [ ] **Step 2: Compile** (build command). Expected: PASS except the `LoginView` call site (fixed in Task 5) — record if so.

- [ ] **Step 3: Commit**
```bash
git add ios/Det695/State/Session.swift
git commit -m "feat(ios): Session 2FA challenge state + verify/resend"
```

---

### Task 5: LoginView — drop TOTP field, present verify sheet

**Files:**
- Modify: `ios/Det695/Views/LoginView.swift`

**Interfaces:**
- Consumes: `session.login(username:password:)` (no totp), `session.challenge`.
- Produces: no inline 2FA field; a `.sheet(item: $session.challenge)` presenting `TwoFactorVerifyView` (Task 6).

- [ ] **Step 1: Remove the TOTP field + focus case** (lines ~47-50) and the `@State totp` / `.totp` focus enum case. Update `submit()`:

```swift
private func submit() {
    focus = nil
    Task { await session.login(username: username, password: password) }
}
```

- [ ] **Step 2: Present the verify sheet.** Add to the view body (alongside the existing `showForgot` sheet ~line 80):

```swift
.sheet(item: $session.challenge) { _ in
    TwoFactorVerifyView()
        .environmentObject(session)
}
```

(`TwoFactorVerifyView` reads `session.challenge`/`verify`/`resend`. Because `challenge` is `Identifiable`, `.sheet(item:)` presents when it becomes non-nil and dismisses when Session sets it to nil after success.)

- [ ] **Step 3: Compile** (build command). Expected: FAIL only on the missing `TwoFactorVerifyView` (created next) — acceptable; or create a stub first. Record status.

- [ ] **Step 4: Commit** (after Task 6 compiles cleanly, or commit a compiling stub now). Prefer committing together with Task 6 if the build can't be green alone:
```bash
git add ios/Det695/Views/LoginView.swift
git commit -m "feat(ios): remove inline TOTP field; present 2FA verify sheet"
```

---

### Task 6: TwoFactorVerifyView (the verify sheet)

**Files:**
- Create: `ios/Det695/Views/TwoFactorVerifyView.swift`

**Interfaces:**
- Consumes: `@EnvironmentObject session` (`challenge`, `verify`, `resend`, `isSubmitting`, `loginError`).
- Produces: code entry (numeric, `.oneTimeCode`), "Trust this device for 30 days" toggle, "Verify" button, "Resend code" with a 60s countdown.

- [ ] **Step 1: Implement**

```swift
import SwiftUI

struct TwoFactorVerifyView: View {
    @EnvironmentObject var session: Session
    @Environment(\.dismiss) private var dismiss
    @State private var code = ""
    @State private var trustDevice = false
    @State private var cooldown = 0
    @State private var ticker: Task<Void, Never>?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("We emailed a 6-digit code to your address. It expires in 10 minutes.")
                        .font(.footnote).foregroundStyle(.secondary)
                    TextField("Verification code", text: $code)
                        .keyboardType(.numberPad)
                        .textContentType(.oneTimeCode)
                        .onChange(of: code) { _, new in
                            code = String(new.filter(\.isNumber).prefix(6))
                        }
                    Toggle("Trust this device for 30 days", isOn: $trustDevice)
                }
                if let err = session.loginError {
                    Section { Text(err).foregroundStyle(.red).font(.footnote) }
                }
                Section {
                    Button {
                        Task { await session.verify(code: code, trustDevice: trustDevice) }
                    } label: {
                        if session.isSubmitting { ProgressView() } else { Text("Verify") }
                    }
                    .disabled(code.count < 6 || session.isSubmitting)

                    Button(cooldown > 0 ? "Resend code (\(cooldown)s)" : "Resend code") {
                        Task {
                            await session.resend()
                            startCooldown()
                        }
                    }
                    .disabled(cooldown > 0)
                }
            }
            .navigationTitle("Two-factor")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        session.challenge = nil
                        dismiss()
                    }
                }
            }
        }
        .onDisappear { ticker?.cancel() }
    }

    private func startCooldown() {
        cooldown = 60
        ticker?.cancel()
        ticker = Task {
            while cooldown > 0 {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                if Task.isCancelled { return }
                await MainActor.run { cooldown -= 1 }
            }
        }
    }
}
```

- [ ] **Step 2: Compile** (build command). Expected: PASS (Task 5 + Task 6 together produce a clean build).

- [ ] **Step 3: Commit**
```bash
git add ios/Det695/Views/TwoFactorVerifyView.swift
git commit -m "feat(ios): 2FA verify sheet with resend countdown + trust toggle"
```

---

### Task 7: First-login enrollment sheet

**Files:**
- Create: `ios/Det695/Views/EnrollmentSheet.swift`
- Modify: `ios/Det695/Views/RootView.swift` (present once from `MainTabView`/`.signedIn`)

**Interfaces:**
- Consumes: `session.user`, `APIClient.enroll/enrollVerify/enrollmentDismiss/me`, `session.applyUpdatedUser`.
- Produces: a `.sheet` shown once when `user.twoFactorEnabled == false && user.twoFactorEnrollmentPrompted == false`; "Enable" → enroll → code entry → verify → refresh user; "Not now" → dismiss → refresh user.

- [ ] **Step 1: Implement `EnrollmentSheet`** with an internal `enum Step { intro, verify }`, mirroring `ForgotPasswordView`'s state-machine style. On enroll success move to `.verify`; on verify/dismiss success call `session.applyUpdatedUser(try await APIClient.shared.me())` and dismiss.

- [ ] **Step 2: Present it once** in `RootView`'s `.signedIn` branch (around line 65) or on `MainTabView`'s `TabView` (line 77):

```swift
.sheet(isPresented: $showEnrollment) { EnrollmentSheet().environmentObject(session) }
.onAppear {
    if let u = session.user, !u.twoFactorEnabled, !u.twoFactorEnrollmentPrompted {
        showEnrollment = true
    }
}
```

Use a `@State private var showEnrollment = false` on that view. After the sheet flips the user's `enrollmentPrompted` (via `applyUpdatedUser`), the `onAppear` gate won't re-trigger on later appearances.

- [ ] **Step 3: Compile** (build command). Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add ios/Det695/Views/EnrollmentSheet.swift ios/Det695/Views/RootView.swift
git commit -m "feat(ios): one-time first-login 2FA enrollment sheet"
```

---

### Task 8: ProfileView — email-2FA section + Trusted Devices

**Files:**
- Modify: `ios/Det695/Views/ProfileView.swift` (rewrite `TwoFactorSection`, lines ~200-311; add a Trusted Devices section)

**Interfaces:**
- Consumes: `APIClient.twoFAStatus/enroll/enrollVerify/disable2FA/listTrustedDevices/revokeTrustedDevice/revokeOtherTrustedDevices`.
- Produces: an email-2FA enable/disable section (enable = enroll → test code → verify; disable = confirm → disable) and a Trusted Devices section (list with label/last-used/expires; per-row revoke; "revoke all others").

- [ ] **Step 1: Rewrite `TwoFactorSection`** to the email model: read `twoFAStatus().enabled`; if off, an "Enable email 2FA" button → `enroll()` → reveal a 6-digit `.oneTimeCode` field → `enrollVerify(code)` → reload; if on, show status + "Turn off" → `disable2FA()` (copy notes trusted devices are signed out) → reload. Reuse the existing numeric-field + `StatusLine` helpers. Remove all `secret`/`otpauthUri` UI.

- [ ] **Step 2: Add a `TrustedDevicesSection`** (only when 2FA enabled): `listTrustedDevices()` into `@State [TrustedDevice]`; a `ForEach` row per device with label + relative last-used + expiry, a swipe/`Button` "Revoke" → `revokeTrustedDevice(id:)` → reload; a "Revoke all other devices" button (shown when `count > 1`) → `revokeOtherTrustedDevices()` → reload.

- [ ] **Step 3: Compile** (build command). Expected: PASS (also clears any transient errors from the Task 1 TOTP-struct removal).

- [ ] **Step 4: Commit**
```bash
git add ios/Det695/Views/ProfileView.swift
git commit -m "feat(ios): email-2FA enable/disable + trusted-device management in Profile"
```

---

### Task 9: AdminView — 2FA toggle + revoke trusted devices

**Files:**
- Modify: `ios/Det695/Views/AdminView.swift`

**Interfaces:**
- Consumes: `updateAdminUser(id:_:)` with `AdminUserUpdate.twoFactorEnabled`; `adminRevokeTrustedDevices(userId:)`.
- Produces: in `EditUserSheet` (and/or the row menu), a "Require email 2FA" toggle sending `{twoFactorEnabled}` via the existing update path, and a "Revoke trusted devices" button (mirror the `unlock()` precedent, ~lines 422-433) calling the admin revoke endpoint with a success `StatusLine`.

- [ ] **Step 1: Add the toggle** — a `Toggle` bound to a local mirror of `user.twoFactorEnabled`, on change build `AdminUserUpdate(twoFactorEnabled: next)` and call `updateAdminUser` then reload (mirror the active-toggle at lines ~193-201).

- [ ] **Step 2: Add the revoke action** — a `Button("Revoke trusted devices")` near the unlock section → `Task { try await APIClient.shared.adminRevokeTrustedDevices(userId: user.id) }` with inline success/error via `StatusLine`.

- [ ] **Step 3: Compile** (build command). Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add ios/Det695/Views/AdminView.swift
git commit -m "feat(ios): admin 2FA toggle + revoke trusted devices"
```

---

## Final verification

- [ ] `cd ios && xcodegen generate && xcodebuild -project Det695.xcodeproj -scheme Det695 -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' build CODE_SIGNING_ALLOWED=NO -quiet` — clean build.
- [ ] Manual UI smoke (documented; needs backend on :8099 and `DET695_API_BASE` pointed at it): enable 2FA in Profile → sign out → sign in → the verify sheet appears, the emailed code works, "trust this device" → next sign-in skips the sheet; Profile lists the trusted device and revokes it; a fresh un-prompted user gets the enrollment sheet once; admin toggle forces 2FA + revoke works.
- [ ] If `xcodebuild` could not run in the execution environment, the final report states that plainly and lists the manual build/smoke steps the user must run locally.

## Spec coverage check

- Login verify sheet (code + resend + countdown + trust) → Tasks 5, 6. First-login ask-once enrollment sheet → Task 7. Profile email enable/disable + trusted devices → Task 8. Admin toggle + revoke → Task 9. Two-step login sum type + trust-token (Keychain, body) → Tasks 1-4. Models/decoding resilience → Task 1.
- **RULINGS:** trust token in Keychain + login body (not cookie); `login` returns a sum type; no XCTest target — verification is XcodeGen + `xcodebuild` compile + review + documented manual smoke.
- **Out of scope:** web client (its own plan); active TOTP; SMS; backup codes; standing up an iOS unit-test target.
