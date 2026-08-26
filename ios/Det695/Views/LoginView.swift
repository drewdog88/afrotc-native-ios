import SwiftUI

/// Sign-in screen. Mirrors the web login: username + password. When the account
/// has email 2FA, `session.login` returns a challenge and we present the verify
/// sheet rather than collecting a code inline.
struct LoginView: View {
    @EnvironmentObject private var session: Session
    @State private var username = ""
    @State private var password = ""
    @State private var showForgot = false
    @FocusState private var focus: Field?

    private enum Field { case username, password }

    var body: some View {
        ZStack {
            Theme.ink.ignoresSafeArea()
            VStack(spacing: 24) {
                VStack(spacing: 10) {
                    Insignia(size: 132)
                    Text("Det 695")
                        .font(.largeTitle.bold())
                        .foregroundStyle(.white)
                    Text("RECRUITING OPS")
                        .font(.caption.weight(.semibold))
                        .tracking(2)
                        .foregroundStyle(Theme.accent)
                    AFROTCWordmark(height: 26)
                        .foregroundStyle(.white.opacity(0.9))
                        .padding(.top, 2)
                }

                VStack(spacing: 12) {
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textContentType(.username)
                        .focused($focus, equals: .username)
                        .submitLabel(.next)
                        .onSubmit { focus = .password }

                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .focused($focus, equals: .password)
                        .submitLabel(.go)
                        .onSubmit { submit() }
                }
                .textFieldStyle(.roundedBorder)

                if let err = session.loginError {
                    Text(err)
                        .font(.footnote)
                        .foregroundStyle(Theme.danger)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                Button(action: submit) {
                    if session.isSubmitting {
                        ProgressView().tint(.white)
                    } else {
                        Text("Sign in").bold()
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.accent)
                .controlSize(.large)
                .frame(maxWidth: .infinity)
                .disabled(session.isSubmitting || username.isEmpty || password.isEmpty)

                Button("Forgot password?") { showForgot = true }
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(Theme.accent)
            }
            .padding(28)
            .frame(maxWidth: 420)
        }
        .sheet(isPresented: $showForgot) { ForgotPasswordView() }
        .sheet(item: $session.challenge) { _ in
            TwoFactorVerifyView()
                .environmentObject(session)
        }
    }

    private func submit() {
        focus = nil
        Task { await session.login(username: username, password: password) }
    }
}
