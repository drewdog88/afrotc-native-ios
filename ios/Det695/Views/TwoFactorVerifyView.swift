import SwiftUI

/// The sign-in 2FA challenge sheet. Presented from `LoginView` when
/// `session.login` returns a challenge instead of tokens: collects the emailed
/// 6-digit code, an optional "trust this device" choice, and a rate-limited
/// resend. Dismisses itself when `Session` clears `challenge` on success.
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
