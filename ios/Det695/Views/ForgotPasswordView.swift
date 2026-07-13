import SwiftUI

/// Self-service password reset, mirroring the web ForgotPassword page. No email —
/// the user proves ownership by answering the security question on their account.
///   Step 1 (identify): enter username/email → the API returns the question.
///   Step 2 (answer): answer it + set a new password → lockout cleared.
///   Step 3 (done): back to sign in.
/// Presented as a sheet from `LoginView`; all calls are unauthenticated.
struct ForgotPasswordView: View {
    @Environment(\.dismiss) private var dismiss

    private enum Step { case identify, answer, done }

    @State private var step: Step = .identify
    @State private var username = ""
    @State private var question = ""
    @State private var answer = ""
    @State private var password = ""
    @State private var confirm = ""
    @State private var error: String?
    @State private var busy = false
    @FocusState private var focus: Field?

    private enum Field { case username, answer, password, confirm }

    var body: some View {
        NavigationStack {
            Form {
                if let error {
                    Section { Text(error).foregroundStyle(Theme.danger) }
                }
                switch step {
                case .identify: identifyStep
                case .answer: answerStep
                case .done: doneStep
                }
            }
            .navigationTitle("Reset password")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(step == .done ? "Done" : "Cancel") { dismiss() }
                }
            }
        }
    }

    // MARK: Step 1 — identify

    private var identifyStep: some View {
        Section {
            TextField("Username or email", text: $username)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
                .textContentType(.username)
                .focused($focus, equals: .username)
                .submitLabel(.continue)
                .onSubmit { identify() }
            Button { identify() } label: {
                HStack {
                    Text("Continue")
                    if busy { Spacer(); ProgressView() }
                }
            }
            .disabled(busy || username.trimmed.isEmpty)
        } header: {
            Text("Find your account")
        } footer: {
            Text("Enter your username or email and we'll ask the security question you set up.")
        }
    }

    // MARK: Step 2 — answer + new password

    private var answerStep: some View {
        Group {
            Section("Your security question") {
                Text(question).foregroundStyle(.secondary)
                TextField("Answer", text: $answer)
                    .autocorrectionDisabled()
                    .focused($focus, equals: .answer)
            }
            Section {
                SecureField("New password", text: $password)
                    .textContentType(.newPassword)
                    .focused($focus, equals: .password)
                SecureField("Confirm new password", text: $confirm)
                    .textContentType(.newPassword)
                    .focused($focus, equals: .confirm)
            } header: {
                Text("New password")
            } footer: {
                Text("Use at least 8 characters. Resetting also clears any lockout on the account.")
            }
            Section {
                Button { reset() } label: {
                    HStack {
                        Text("Reset password")
                        if busy { Spacer(); ProgressView() }
                    }
                }
                .disabled(busy || answer.trimmed.isEmpty || password.isEmpty || confirm.isEmpty)
            }
        }
    }

    // MARK: Step 3 — done

    private var doneStep: some View {
        Section {
            Label("Password reset", systemImage: "checkmark.seal.fill")
                .foregroundStyle(Theme.ok)
                .font(.headline)
            Text("Your password has been updated and any lockout cleared. You can sign in now.")
                .foregroundStyle(.secondary)
            Button("Go to sign in") { dismiss() }
                .buttonStyle(.borderedProminent)
                .tint(Theme.accent)
        }
    }

    // MARK: Actions

    private func identify() {
        guard !username.trimmed.isEmpty else { return }
        focus = nil
        error = nil
        busy = true
        Task {
            defer { busy = false }
            do {
                let res = try await APIClient.shared.forgotPassword(username: username.trimmed)
                question = res.secretQuestion
                withAnimation { step = .answer }
                focus = .answer
            } catch {
                self.error = message(error, fallback: "We couldn't find an account for that username or email.")
            }
        }
    }

    private func reset() {
        error = nil
        guard password == confirm else {
            error = "The new password and confirmation don't match."
            return
        }
        guard password.count >= 8 else {
            error = "Use at least 8 characters for the new password."
            return
        }
        focus = nil
        busy = true
        Task {
            defer { busy = false }
            do {
                try await APIClient.shared.resetPassword(username: username.trimmed,
                                                         secretAnswer: answer.trimmed,
                                                         newPassword: password)
                withAnimation { step = .done }
            } catch {
                self.error = message(error, fallback: "Couldn't reset your password. Check your answer and try again.")
            }
        }
    }

    private func message(_ error: Error, fallback: String) -> String {
        (error as? APIError)?.errorDescription ?? fallback
    }
}

private extension String {
    /// Local trim helper — the `.trimmed` in ProfileView/ContactsView is fileprivate.
    var trimmed: String { trimmingCharacters(in: .whitespacesAndNewlines) }
}
