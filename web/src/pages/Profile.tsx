/* Profile + security — self-service account settings for the signed-in user.
   Three cards: view/edit profile (name, email, phone), change password (with a
   client-side match check), and two-factor auth lifecycle. Enabling 2FA calls
   /profile/2fa/setup to mint a TOTP secret, shows it as selectable monospace text
   for manual entry into an authenticator app, then verifies the 6-digit code. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type UserOut } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./Profile.module.css";

type ProfileUpdate = components["schemas"]["ProfileUpdate"];
type PasswordChange = components["schemas"]["PasswordChange"];
type TwoFAStatus = components["schemas"]["TwoFAStatus"];
type TwoFASetupResponse = components["schemas"]["TwoFASetupResponse"];
type TwoFAVerifyRequest = components["schemas"]["TwoFAVerifyRequest"];

type Toast = { kind: "ok" | "error"; msg: string } | null;

function errMsg(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function Profile() {
  const { user: authUser } = useAuth();
  const [toast, setToast] = useState<Toast>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-dismiss the toast a few seconds after it appears.
  useEffect(() => {
    if (!toast) return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(null), 4200);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [toast]);

  const notify = (kind: "ok" | "error", msg: string) => setToast({ kind, msg });

  const profileQ = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.get<UserOut>("/profile"),
    // Seed the first paint from the already-loaded auth user so there's no flash.
    initialData: authUser ?? undefined,
  });

  const user = profileQ.data;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Profile and security</h1>
          <p className={styles.subtitle}>Manage your account details, password, and two-factor authentication.</p>
        </div>
      </div>

      {profileQ.isLoading && !user ? (
        <>
          <div className={`card ${styles.skeleton}`} style={{ height: 220 }} />
          <div className={`card ${styles.skeleton}`} style={{ height: 240 }} />
          <div className={`card ${styles.skeleton}`} style={{ height: 180 }} />
        </>
      ) : profileQ.isError || !user ? (
        <div className={styles.formError}>Couldn't load your profile. Check that you're signed in and the API is running.</div>
      ) : (
        <>
          <ProfileCard user={user} notify={notify} />
          <PasswordCard notify={notify} />
          <TwoFactorCard notify={notify} />
        </>
      )}

      {toast && (
        <div
          className={`${styles.toast} ${toast.kind === "ok" ? styles.toastOk : styles.toastErr}`}
          role="status"
          aria-live="polite"
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

/* ---- Profile: view + edit name / email / phone ---- */
function ProfileCard({ user, notify }: { user: UserOut; notify: (k: "ok" | "error", m: string) => void }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    phone: user.phone ?? "",
  });

  // Re-sync from the server copy whenever we're not mid-edit.
  useEffect(() => {
    if (!editing) {
      setForm({
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email,
        phone: user.phone ?? "",
      });
    }
  }, [user, editing]);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: (body: ProfileUpdate) => api.patch<UserOut>("/profile", body),
    onSuccess: (updated) => {
      qc.setQueryData(["profile"], updated);
      qc.invalidateQueries({ queryKey: ["profile"] });
      setEditing(false);
      notify("ok", "Profile updated.");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't save your profile.")),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    save.mutate({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
    });
  }

  if (!editing) {
    return (
      <section className={`card ${styles.panel}`}>
        <div className={styles.panelHead}>
          <div>
            <h2 className={styles.panelTitle}>Profile</h2>
            <span className={styles.panelNote}>@{user.username} · {user.role}</span>
          </div>
          <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>
        </div>
        <div className={styles.fields}>
          <Field label="First name" value={user.first_name} />
          <Field label="Last name" value={user.last_name} />
          <Field label="Email" value={user.email} />
          <Field label="Phone" value={user.phone} />
        </div>
      </section>
    );
  }

  return (
    <form className={`card ${styles.panel}`} onSubmit={onSubmit}>
      <div className={styles.panelHead}>
        <h2 className={styles.panelTitle}>Edit profile</h2>
      </div>
      <div className={styles.fields}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pf_first">First name</label>
          <input id="pf_first" className="input" value={form.first_name} onChange={set("first_name")} required autoFocus />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pf_last">Last name</label>
          <input id="pf_last" className="input" value={form.last_name} onChange={set("last_name")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pf_email">Email</label>
          <input id="pf_email" className="input" type="email" value={form.email} onChange={set("email")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pf_phone">Phone</label>
          <input id="pf_phone" className="input" value={form.phone} onChange={set("phone")} />
        </div>
      </div>
      <div className={styles.actions}>
        <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)} disabled={save.isPending}>Cancel</button>
        <button type="submit" className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

/* ---- Change password ---- */
function PasswordCard({ notify }: { notify: (k: "ok" | "error", m: string) => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const mismatch = confirm.length > 0 && next !== confirm;

  const change = useMutation({
    mutationFn: (body: PasswordChange) => api.post("/auth/change-password", body),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      setConfirm("");
      setLocalError(null);
      notify("ok", "Password changed.");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't change your password.")),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    if (next !== confirm) {
      setLocalError("The new password and confirmation don't match.");
      return;
    }
    if (next.length < 8) {
      setLocalError("Use at least 8 characters for the new password.");
      return;
    }
    change.mutate({ current_password: current, new_password: next });
  }

  return (
    <form className={`card ${styles.panel}`} onSubmit={onSubmit}>
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Change password</h2>
          <span className={styles.panelNote}>Use a strong password you don't reuse elsewhere.</span>
        </div>
      </div>
      {localError && <div className={styles.formError}>{localError}</div>}
      <div className={styles.stack}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pw_current">Current password</label>
          <input
            id="pw_current"
            className="input"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pw_new">New password</label>
          <input
            id="pw_new"
            className="input"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
          />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="pw_confirm">Confirm new password</label>
          <input
            id="pw_confirm"
            className={`input ${mismatch ? styles.inputError : ""}`}
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className={styles.hintError}>Passwords don't match yet.</span>}
        </div>
      </div>
      <div className={styles.actions}>
        <button type="submit" className="btn btn-primary" disabled={change.isPending || mismatch}>
          {change.isPending ? "Updating…" : "Update password"}
        </button>
      </div>
    </form>
  );
}

/* ---- Two-factor authentication lifecycle ---- */
function TwoFactorCard({ notify }: { notify: (k: "ok" | "error", m: string) => void }) {
  const qc = useQueryClient();
  const [setup, setSetup] = useState<TwoFASetupResponse | null>(null);
  const [code, setCode] = useState("");

  const statusQ = useQuery({
    queryKey: ["profile-2fa"],
    queryFn: () => api.get<TwoFAStatus>("/profile/2fa"),
  });
  const enabled = statusQ.data?.enabled ?? false;

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["profile-2fa"] });
    qc.invalidateQueries({ queryKey: ["profile"] });
  };

  const beginSetup = useMutation({
    mutationFn: () => api.post<TwoFASetupResponse>("/profile/2fa/setup"),
    onSuccess: (res) => {
      setSetup(res);
      setCode("");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't start two-factor setup.")),
  });

  const verify = useMutation({
    mutationFn: (body: TwoFAVerifyRequest) => api.post("/profile/2fa/verify", body),
    onSuccess: () => {
      setSetup(null);
      setCode("");
      invalidate();
      notify("ok", "Two-factor authentication is on.");
    },
    onError: (err) => notify("error", errMsg(err, "That code didn't verify. Try the current one.")),
  });

  const disable = useMutation({
    mutationFn: () => api.post("/profile/2fa/disable"),
    onSuccess: () => {
      setSetup(null);
      setCode("");
      invalidate();
      notify("ok", "Two-factor authentication is off.");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't turn off two-factor authentication.")),
  });

  function onVerify(e: FormEvent) {
    e.preventDefault();
    verify.mutate({ code: code.trim() });
  }

  return (
    <section className={`card ${styles.panel}`}>
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Two-factor authentication</h2>
          <span className={styles.panelNote}>Add a time-based code from an authenticator app on top of your password.</span>
        </div>
        {!statusQ.isLoading && (
          <span className={`${styles.badge} ${enabled ? styles.badgeOn : styles.badgeOff}`}>
            <span className={styles.badgeDot} aria-hidden />
            {enabled ? "Enabled" : "Disabled"}
          </span>
        )}
      </div>

      {statusQ.isLoading ? (
        <div className={styles.skeleton} style={{ height: 96, borderRadius: "var(--r-md)" }} />
      ) : enabled ? (
        <div className={styles.stack}>
          <p className={styles.note}>
            Your account is protected. You'll be asked for a 6-digit code when you sign in.
          </p>
          <div className={styles.actions}>
            <button
              className="btn btn-ghost"
              onClick={() => disable.mutate()}
              disabled={disable.isPending}
            >
              {disable.isPending ? "Turning off…" : "Turn off two-factor"}
            </button>
          </div>
        </div>
      ) : setup ? (
        <form className={styles.stack} onSubmit={onVerify}>
          <p className={styles.note}>
            Add this account to your authenticator app, then enter the 6-digit code it shows to finish.
          </p>
          <div className={styles.field}>
            <span className="field-label">Manual entry key</span>
            <code className={styles.secret}>{setup.secret}</code>
          </div>
          <div className={styles.field}>
            <span className="field-label">Setup URI (otpauth)</span>
            <code className={styles.uri}>{setup.otpauth_uri}</code>
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="tfa_code">6-digit code</label>
            <input
              id="tfa_code"
              className={`input ${styles.codeInput}`}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              maxLength={6}
              autoFocus
            />
          </div>
          <div className={styles.actions}>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setSetup(null);
                setCode("");
              }}
              disabled={verify.isPending}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={verify.isPending || code.length !== 6}>
              {verify.isPending ? "Verifying…" : "Verify and enable"}
            </button>
          </div>
        </form>
      ) : (
        <div className={styles.stack}>
          <p className={styles.note}>
            Two-factor is off. Turn it on to require a rotating code from your phone at sign-in.
          </p>
          <div className={styles.actions}>
            <button
              className="btn btn-accent"
              onClick={() => beginSetup.mutate()}
              disabled={beginSetup.isPending}
            >
              {beginSetup.isPending ? "Preparing…" : "Set up two-factor"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldLabel}>{label}</div>
      <div className={styles.fieldValue}>{value || <span className={styles.muted}>—</span>}</div>
    </div>
  );
}
