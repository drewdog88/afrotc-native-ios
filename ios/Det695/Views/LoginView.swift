import SwiftUI

/// Sign-in screen. Mirrors the web login: username + password, optional TOTP.
struct LoginView: View {
    @EnvironmentObject private var session: Session
    @State private var username = ""
    @State private var password = ""
    @State private var totp = ""
    @FocusState private var focus: Field?

    private enum Field { case username, password, totp }

    var body: some View {
        ZStack {
            Theme.ink.ignoresSafeArea()
            VStack(spacing: 24) {
                VStack(spacing: 6) {
                    Image(systemName: "chevron.up.circle.fill")
                        .font(.system(size: 44))
                        .foregroundStyle(Theme.accent)
                    Text("Det 695")
                        .font(.largeTitle.bold())
                        .foregroundStyle(.white)
                    Text("RECRUITING OPS")
                        .font(.caption.weight(.semibold))
                        .tracking(2)
                        .foregroundStyle(Theme.accent)
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

                    TextField("2FA code (if enabled)", text: $totp)
                        .keyboardType(.numberPad)
                        .focused($focus, equals: .totp)
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
            }
            .padding(28)
            .frame(maxWidth: 420)
        }
    }

    private func submit() {
        focus = nil
        Task { await session.login(username: username, password: password, totpCode: totp) }
    }
}
