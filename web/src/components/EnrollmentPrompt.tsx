/* One-time first-login modal that invites a user to enroll in email 2FA.
   Shown once on the first authenticated screen for a user who hasn't enabled
   2FA and hasn't already been prompted (per two_factor_enabled /
   two_factor_enrollment_prompted on the auth user). "Enable now" starts
   enrollment and walks the user through a 6-digit email code; "Not now"
   dismisses the prompt for good. Either path refreshes the auth user so the
   gate condition flips and the modal doesn't reappear. */
import { useEffect, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

type Step = "intro" | "verify";
type Toast = { kind: "ok" | "error"; msg: string } | null;

function errMsg(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function EnrollmentPrompt() {
  const { user, refresh } = useAuth();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("intro");
  const [code, setCode] = useState("");
  const [toast, setToast] = useState<Toast>(null);

  useEffect(() => {
    if (user && !user.two_factor_enabled && !user.two_factor_enrollment_prompted) setOpen(true);
  }, [user]);

  const notify = (kind: "ok" | "error", msg: string) => setToast({ kind, msg });

  const enroll = useMutation({
    mutationFn: () => api.twoFAEnroll(),
    onSuccess: () => {
      setCode("");
      setToast(null);
      setStep("verify");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't start email two-factor setup.")),
  });

  const verify = useMutation({
    mutationFn: (c: string) => api.twoFAEnrollVerify(c),
    onSuccess: async () => {
      await refresh();
      setOpen(false);
    },
    onError: (err) => notify("error", errMsg(err, "That code didn't verify. Try the current one.")),
  });

  const dismiss = useMutation({
    mutationFn: () => api.twoFAEnrollmentDismiss(),
    onSuccess: async () => {
      await refresh();
      setOpen(false);
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't dismiss the prompt.")),
  });

  if (!open || !user) return null;

  function onVerify(e: FormEvent) {
    e.preventDefault();
    verify.mutate(code.trim());
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="enrollment-prompt-title"
    >
      <div className="card" style={{ maxWidth: 440, width: "90%" }}>
        {step === "intro" ? (
          <>
            <h2 id="enrollment-prompt-title">Add email two-factor authentication</h2>
            <p className="muted">
              Protect your account with a one-time code sent to your email each time you sign in.
              You can turn this on now or set it up later from your profile.
            </p>
            {toast?.kind === "error" && <div className="form-error">{toast.msg}</div>}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => dismiss.mutate()}
                disabled={dismiss.isPending}
              >
                {dismiss.isPending ? "Dismissing…" : "Not now"}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => enroll.mutate()}
                disabled={enroll.isPending}
              >
                {enroll.isPending ? "Starting…" : "Enable now"}
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={onVerify}>
            <h2 id="enrollment-prompt-title">Enter your verification code</h2>
            <p className="muted">We emailed a 6-digit code to your address. It expires shortly.</p>
            <label className="field-label" htmlFor="enrollment_code">
              Verification code
            </label>
            <input
              id="enrollment_code"
              className="input"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="000000"
              autoFocus
            />
            {toast?.kind === "error" && <div className="form-error">{toast.msg}</div>}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => dismiss.mutate()}
                disabled={dismiss.isPending || verify.isPending}
              >
                {dismiss.isPending ? "Dismissing…" : "Not now"}
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={verify.isPending || code.length !== 6}
              >
                {verify.isPending ? "Verifying…" : "Verify"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
