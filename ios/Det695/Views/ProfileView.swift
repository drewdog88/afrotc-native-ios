import SwiftUI

/// Self-service account settings, mirroring the web Profile page
/// (web/src/pages/Profile.tsx): view/edit profile, change password, the email
/// two-factor lifecycle (enable/disable + trusted-device management) — plus the
/// Sign Out action the app otherwise lacks.
/// A `Form` with one section per web "card"; each action reports its result inline
/// rather than via a global toast (the idiomatic pattern for a form).
struct ProfileView: View {
    @EnvironmentObject private var session: Session
    @State private var user: UserOut?
    @State private var loadError: String?
    @State private var loading = false
    @State private var confirmSignOut = false
    @State private var twoFAEnabled = false

    var body: some View {
        Group {
            if let user {
                Form {
                    ProfileSection(user: user) { updated in
                        self.user = updated
                        session.applyUpdatedUser(updated)
                    }
                    PasswordSection()
                    TwoFactorSection(onEnabledChange: { twoFAEnabled = $0 })
                    if twoFAEnabled { TrustedDevicesSection() }
                    signOutSection
                }
            } else if let loadError {
                ContentUnavailableView {
                    Label("Couldn't load your profile", systemImage: "person.crop.circle.badge.exclamationmark")
                } description: {
                    Text(loadError)
                }
            } else {
                ProgressView()
            }
        }
        .navigationTitle("Profile & Security")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private var signOutSection: some View {
        Section {
            Button(role: .destructive) { confirmSignOut = true } label: {
                Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                    .frame(maxWidth: .infinity)
            }
            .confirmationDialog("Sign out of Det 695?", isPresented: $confirmSignOut, titleVisibility: .visible) {
                Button("Sign out", role: .destructive) { Task { await session.logout() } }
                Button("Cancel", role: .cancel) {}
            }
        }
    }

    private func load() async {
        // Seed instantly from the already-loaded auth user so there's no flash,
        // then confirm/refresh against the server (mirrors the web's initialData).
        if user == nil { user = session.user }
        loading = true
        defer { loading = false }
        do { user = try await APIClient.shared.profile() }
        catch {
            if user == nil { loadError = (error as? APIError)?.errorDescription ?? error.localizedDescription }
        }
    }
}

// MARK: - Profile (view + edit)

private struct ProfileSection: View {
    let user: UserOut
    let onSaved: (UserOut) -> Void

    @State private var editing = false
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var saving = false
    @State private var status: StatusLine?

    var body: some View {
        Section {
            if editing {
                TextField("First name", text: $firstName).textContentType(.givenName)
                TextField("Last name", text: $lastName).textContentType(.familyName)
                TextField("Email", text: $email)
                    .textContentType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.emailAddress)
                TextField("Phone", text: $phone)
                    .textContentType(.telephoneNumber)
                    .keyboardType(.phonePad)
                HStack {
                    Button("Cancel") { editing = false }.disabled(saving)
                    Spacer()
                    Button { Task { await save() } } label: {
                        if saving { ProgressView() } else { Text("Save").bold() }
                    }
                    .disabled(saving || firstName.trimmed.isEmpty || lastName.trimmed.isEmpty || email.trimmed.isEmpty)
                }
            } else {
                LabeledContent("First name", value: user.firstName)
                LabeledContent("Last name", value: user.lastName)
                LabeledContent("Email", value: user.email)
                LabeledContent("Phone", value: user.phone?.nonEmpty ?? "—")
            }
            if let status { status }
        } header: {
            HStack {
                Text("Profile")
                Spacer()
                if !editing {
                    Button("Edit") { beginEdit() }
                        .font(.footnote.weight(.semibold))
                        .textCase(nil)
                }
            }
        } footer: {
            if !editing { Text("@\(user.username) · \(user.role)") }
        }
    }

    private func beginEdit() {
        firstName = user.firstName
        lastName = user.lastName
        email = user.email
        phone = user.phone ?? ""
        status = nil
        editing = true
    }

    private func save() async {
        saving = true
        defer { saving = false }
        let body = ProfileUpdate(firstName: firstName.trimmed,
                                 lastName: lastName.trimmed,
                                 email: email.trimmed,
                                 phone: phone.trimmed.nonEmpty)
        do {
            let updated = try await APIClient.shared.updateProfile(body)
            onSaved(updated)
            editing = false
            status = .ok("Profile updated.")
        } catch {
            status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }
}

// MARK: - Change password

private struct PasswordSection: View {
    @State private var current = ""
    @State private var next = ""
    @State private var confirm = ""
    @State private var saving = false
    @State private var status: StatusLine?

    private var mismatch: Bool { !confirm.isEmpty && next != confirm }

    var body: some View {
        Section {
            SecureField("Current password", text: $current).textContentType(.password)
            SecureField("New password", text: $next).textContentType(.newPassword)
            SecureField("Confirm new password", text: $confirm).textContentType(.newPassword)
            if mismatch { Text("Passwords don't match yet.").font(.caption).foregroundStyle(Theme.danger) }
            Button { Task { await change() } } label: {
                if saving { ProgressView() } else { Text("Update password") }
            }
            .disabled(saving || current.isEmpty || next.isEmpty || confirm.isEmpty || mismatch)
            if let status { status }
        } header: {
            Text("Change password")
        } footer: {
            Text("Use a strong password you don't reuse elsewhere.")
        }
    }

    private func change() async {
        status = nil
        guard next == confirm else { status = .error("The new password and confirmation don't match."); return }
        guard next.count >= 8 else { status = .error("Use at least 8 characters for the new password."); return }
        saving = true
        defer { saving = false }
        do {
            try await APIClient.shared.changePassword(.init(currentPassword: current, newPassword: next))
            current = ""; next = ""; confirm = ""
            status = .ok("Password changed.")
        } catch {
            status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }
}

// MARK: - Two-factor authentication

private struct TwoFactorSection: View {
    /// Notifies the parent when the enabled state is known/changes, so it can
    /// show or hide the Trusted Devices section accordingly.
    let onEnabledChange: (Bool) -> Void

    @State private var enabled = false
    @State private var loading = true
    @State private var working = false
    /// True once enrollment has begun (a code was emailed) and we're awaiting
    /// the 6-digit confirmation code.
    @State private var enrolling = false
    @State private var code = ""
    @State private var status: StatusLine?

    var body: some View {
        Section {
            if loading {
                HStack { ProgressView(); Text("Checking…").foregroundStyle(.secondary) }
            } else if enabled {
                Text("Your account is protected. We'll email you a 6-digit code when you sign in on a new device.")
                    .font(.footnote).foregroundStyle(.secondary)
                Button(role: .destructive) { Task { await disable() } } label: {
                    if working { ProgressView() } else { Text("Turn off two-factor") }
                }.disabled(working)
            } else if enrolling {
                Text("We emailed a 6-digit code to your address. Enter it below to finish turning on two-factor.")
                    .font(.footnote).foregroundStyle(.secondary)
                TextField("000000", text: $code)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .font(.title3.monospacedDigit())
                    .onChange(of: code) { _, v in code = String(v.filter(\.isNumber).prefix(6)) }
                HStack {
                    Button("Cancel") { enrolling = false; code = ""; status = nil }.disabled(working)
                    Spacer()
                    Button { Task { await verifyEnroll() } } label: {
                        if working { ProgressView() } else { Text("Verify & enable").bold() }
                    }.disabled(working || code.count != 6)
                }
            } else {
                Text("Two-factor is off. Turn it on to require an emailed code when you sign in on a new device.")
                    .font(.footnote).foregroundStyle(.secondary)
                Button { Task { await beginEnroll() } } label: {
                    if working { ProgressView() } else { Text("Enable email 2FA") }
                }.disabled(working)
            }
            if let status { status }
        } header: {
            HStack {
                Text("Two-factor authentication")
                Spacer()
                if !loading {
                    Label(enabled ? "Enabled" : "Disabled", systemImage: enabled ? "checkmark.shield.fill" : "shield.slash")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(enabled ? Theme.ok : Theme.muted)
                        .textCase(nil)
                }
            }
        }
        .task { await loadStatus() }
    }

    private func loadStatus() async {
        loading = true
        defer { loading = false }
        do {
            enabled = try await APIClient.shared.twoFAStatus().enabled
            onEnabledChange(enabled)
        } catch { status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription) }
    }

    private func beginEnroll() async {
        working = true; status = nil
        defer { working = false }
        do {
            try await APIClient.shared.enroll()
            enrolling = true; code = ""
        } catch { status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription) }
    }

    private func verifyEnroll() async {
        working = true; status = nil
        defer { working = false }
        do {
            try await APIClient.shared.enrollVerify(code: code.trimmed)
            enrolling = false; code = ""
            await loadStatus()
            status = .ok("Two-factor authentication is on.")
        } catch {
            status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }

    private func disable() async {
        working = true; status = nil
        defer { working = false }
        do {
            try await APIClient.shared.disable2FA()
            enrolling = false; code = ""
            await loadStatus()
            status = .ok("Two-factor is off. Your trusted devices were signed out.")
        } catch {
            status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }
}

// MARK: - Trusted devices

private struct TrustedDevicesSection: View {
    @State private var devices: [TrustedDevice] = []
    @State private var loading = true
    @State private var working = false
    @State private var status: StatusLine?

    var body: some View {
        Section {
            if loading {
                HStack { ProgressView(); Text("Loading…").foregroundStyle(.secondary) }
            } else if devices.isEmpty {
                Text("No trusted devices yet. Check \"Trust this device\" when you sign in to skip the emailed code here for 30 days.")
                    .font(.footnote).foregroundStyle(.secondary)
            } else {
                ForEach(devices) { device in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(device.deviceLabel.nonEmpty ?? "Unknown device")
                        Text("Last used \(DateDisplay.mediumDateTime(device.lastUsedAt)) · Expires \(DateDisplay.mediumDate(device.expiresAt))")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button(role: .destructive) { Task { await revoke(id: device.id) } } label: {
                            Label("Revoke", systemImage: "trash")
                        }
                    }
                }
                if devices.count > 1 {
                    Button(role: .destructive) { Task { await revokeOthers() } } label: {
                        if working { ProgressView() } else { Text("Revoke all other devices") }
                    }.disabled(working)
                }
            }
            if let status { status }
        } header: {
            Text("Trusted devices")
        } footer: {
            Text("Swipe a device to revoke it. Revoking signs it out and requires an emailed code on its next sign-in.")
        }
        .task { await load() }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do { devices = try await APIClient.shared.listTrustedDevices() }
        catch { status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription) }
    }

    private func revoke(id: Int) async {
        working = true; status = nil
        defer { working = false }
        do {
            try await APIClient.shared.revokeTrustedDevice(id: id)
            await load()
            status = .ok("Device revoked.")
        } catch {
            status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }

    private func revokeOthers() async {
        working = true; status = nil
        defer { working = false }
        do {
            try await APIClient.shared.revokeOtherTrustedDevices()
            await load()
            status = .ok("Other devices revoked.")
        } catch {
            status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }
}

// MARK: - Shared inline status line

/// A small success/failure line shown under the section that produced it.
private struct StatusLine: View {
    enum Kind { case ok, error }
    let kind: Kind
    let text: String

    static func ok(_ t: String) -> StatusLine { .init(kind: .ok, text: t) }
    static func error(_ t: String) -> StatusLine { .init(kind: .error, text: t) }

    var body: some View {
        Label(text, systemImage: kind == .ok ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
            .font(.footnote)
            .foregroundStyle(kind == .ok ? Theme.ok : Theme.danger)
    }
}

private extension String {
    var trimmed: String { trimmingCharacters(in: .whitespacesAndNewlines) }
    /// nil when the (already-trimmed) string is empty — for optional payload fields.
    var nonEmpty: String? { isEmpty ? nil : self }
}
