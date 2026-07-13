import SwiftUI
import UIKit

/// Self-service account settings, mirroring the web Profile page
/// (web/src/pages/Profile.tsx): view/edit profile, change password, and the full
/// two-factor (TOTP) lifecycle — plus the Sign Out action the app otherwise lacks.
/// A `Form` with one section per web "card"; each action reports its result inline
/// rather than via a global toast (the idiomatic pattern for a form).
struct ProfileView: View {
    @EnvironmentObject private var session: Session
    @State private var user: UserOut?
    @State private var loadError: String?
    @State private var loading = false
    @State private var confirmSignOut = false

    var body: some View {
        Group {
            if let user {
                Form {
                    ProfileSection(user: user) { updated in
                        self.user = updated
                        session.applyUpdatedUser(updated)
                    }
                    PasswordSection()
                    TwoFactorSection()
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
    @State private var enabled = false
    @State private var loading = true
    @State private var working = false
    @State private var setup: TwoFASetupResponse?
    @State private var code = ""
    @State private var status: StatusLine?

    var body: some View {
        Section {
            if loading {
                HStack { ProgressView(); Text("Checking…").foregroundStyle(.secondary) }
            } else if enabled {
                Text("Your account is protected. You'll be asked for a 6-digit code when you sign in.")
                    .font(.footnote).foregroundStyle(.secondary)
                Button(role: .destructive) { Task { await disable() } } label: {
                    if working { ProgressView() } else { Text("Turn off two-factor") }
                }.disabled(working)
            } else if let setup {
                Text("Add this account to your authenticator app, then enter the 6-digit code it shows to finish.")
                    .font(.footnote).foregroundStyle(.secondary)
                copyableRow(label: "Manual entry key", value: setup.secret)
                copyableRow(label: "Setup URI", value: setup.otpauthUri)
                TextField("000000", text: $code)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .font(.title3.monospacedDigit())
                    .onChange(of: code) { _, v in code = String(v.filter(\.isNumber).prefix(6)) }
                HStack {
                    Button("Cancel") { self.setup = nil; code = "" }.disabled(working)
                    Spacer()
                    Button { Task { await verify() } } label: {
                        if working { ProgressView() } else { Text("Verify & enable").bold() }
                    }.disabled(working || code.count != 6)
                }
            } else {
                Text("Two-factor is off. Turn it on to require a rotating code from your phone at sign-in.")
                    .font(.footnote).foregroundStyle(.secondary)
                Button { Task { await beginSetup() } } label: {
                    if working { ProgressView() } else { Text("Set up two-factor") }
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

    private func copyableRow(label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            HStack {
                Text(value).font(.footnote.monospaced()).textSelection(.enabled)
                    .lineLimit(2).truncationMode(.middle)
                Spacer()
                Button { UIPasteboard.general.string = value } label: {
                    Image(systemName: "doc.on.doc")
                }.buttonStyle(.borderless)
            }
        }
    }

    private func loadStatus() async {
        loading = true
        defer { loading = false }
        do { enabled = try await APIClient.shared.twoFAStatus().enabled }
        catch { status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription) }
    }

    private func beginSetup() async {
        working = true; status = nil
        defer { working = false }
        do { setup = try await APIClient.shared.twoFASetup(); code = "" }
        catch { status = .error((error as? APIError)?.errorDescription ?? error.localizedDescription) }
    }

    private func verify() async {
        working = true; status = nil
        defer { working = false }
        do {
            try await APIClient.shared.twoFAVerify(.init(code: code.trimmed))
            setup = nil; code = ""
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
            try await APIClient.shared.twoFADisable()
            setup = nil; code = ""
            await loadStatus()
            status = .ok("Two-factor authentication is off.")
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
