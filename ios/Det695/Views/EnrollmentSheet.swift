import SwiftUI

/// The one-time nudge to turn on email two-factor, shown right after a user's
/// first sign-in (gated on `twoFactorEnabled == false && twoFactorEnrollmentPrompted
/// == false`). Mirrors `ForgotPasswordView`'s step-machine style.
///   Step 1 (intro): explain email 2FA → "Enable" emails a code and moves on,
///     or "Not now" records the prompt so it won't reappear.
///   Step 2 (verify): enter the emailed 6-digit code to finish.
/// Either terminal action refreshes the cached user (so `enrollmentPrompted`
/// flips and the gate won't re-fire) before dismissing.
struct EnrollmentSheet: View {
    @EnvironmentObject private var session: Session
    @Environment(\.dismiss) private var dismiss

    private enum Step { case intro, verify }

    @State private var step: Step = .intro
    @State private var code = ""
    @State private var error: String?
    @State private var busy = false
    @FocusState private var codeFocused: Bool

    var body: some View {
        NavigationStack {
            Form {
                if let error {
                    Section { Text(error).foregroundStyle(Theme.danger) }
                }
                switch step {
                case .intro: introStep
                case .verify: verifyStep
                }
            }
            .navigationTitle("Secure your account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Not now") { declineAndClose() }
                        .disabled(busy)
                }
            }
        }
        .interactiveDismissDisabled(busy)
    }

    // MARK: Step 1 — intro

    private var introStep: some View {
        Section {
            Label("Email two-factor", systemImage: "envelope.badge.shield.half.filled")
                .font(.headline)
            Text("Add a second step at sign-in: we'll email you a 6-digit code when you log in on a new device. You can turn it on now or later from Profile & Security.")
                .foregroundStyle(.secondary)
            Button { enable() } label: {
                HStack {
                    Text("Enable email 2FA")
                    if busy { Spacer(); ProgressView() }
                }
            }
            .disabled(busy)
        } footer: {
            Text("Trusted devices skip the code for 30 days.")
        }
    }

    // MARK: Step 2 — verify

    private var verifyStep: some View {
        Section {
            Text("We emailed a 6-digit code to your address. It expires in 10 minutes.")
                .font(.footnote).foregroundStyle(.secondary)
            TextField("Verification code", text: $code)
                .keyboardType(.numberPad)
                .textContentType(.oneTimeCode)
                .font(.title3.monospacedDigit())
                .focused($codeFocused)
                .onChange(of: code) { _, new in code = String(new.filter(\.isNumber).prefix(6)) }
            Button { verify() } label: {
                HStack {
                    Text("Verify & enable")
                    if busy { Spacer(); ProgressView() }
                }
            }
            .disabled(busy || code.count != 6)
        } header: {
            Text("Enter your code")
        }
    }

    // MARK: Actions

    private func enable() {
        error = nil
        busy = true
        Task {
            defer { busy = false }
            do {
                try await APIClient.shared.enroll()
                withAnimation { step = .verify }
                codeFocused = true
            } catch {
                self.error = message(error, fallback: "Couldn't start enrollment. Please try again.")
            }
        }
    }

    private func verify() {
        error = nil
        busy = true
        Task {
            defer { busy = false }
            do {
                try await APIClient.shared.enrollVerify(code: code)
                await refreshUser()
                dismiss()
            } catch {
                self.error = message(error, fallback: "That code didn't match. Check your email and try again.")
            }
        }
    }

    /// "Not now" — record that we prompted (so this sheet won't reappear), then
    /// close. Dismisses even if the network call fails; the nudge is optional.
    private func declineAndClose() {
        busy = true
        Task {
            defer { busy = false }
            try? await APIClient.shared.enrollmentDismiss()
            await refreshUser()
            dismiss()
        }
    }

    /// Pull the fresh user so `twoFactorEnabled`/`twoFactorEnrollmentPrompted`
    /// reflect the change and the RootView gate won't re-trigger.
    private func refreshUser() async {
        if let updated = try? await APIClient.shared.me() {
            session.applyUpdatedUser(updated)
        }
    }

    private func message(_ error: Error, fallback: String) -> String {
        (error as? APIError)?.errorDescription ?? fallback
    }
}
