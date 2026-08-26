/* Profile + security — self-service account settings for the signed-in user.
   Cards: view/edit profile (name, email, phone), change password (with a
   client-side match check), email two-factor auth lifecycle, and (when 2FA is
   on) trusted-device management. Enabling 2FA calls /profile/2fa/enroll to
   email a 6-digit code, then /profile/2fa/enroll/verify to confirm it. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type UserOut } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./Profile.module.css";

type ProfileUpdate = components["schemas"]["ProfileUpdate"];
type PasswordChange = components["schemas"]["PasswordChange"];

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

  // Shared with TwoFactorCard's own query (same key, same cache entry) so the
  // parent can decide whether to show the Trusted devices card without an
  // extra round trip.
  const twoFAQ = useQuery({
    queryKey: ["profile-2fa"],
    queryFn: () => api.twoFAStatus(),
  });

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
          <SignedInDevicesCard notify={notify} />
          {twoFAQ.data?.enabled && <TrustedDevicesCard />}
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

/* ---- Two-factor authentication lifecycle (email-based) ---- */
function TwoFactorCard({ notify }: { notify: (k: "ok" | "error", m: string) => void }) {
  const qc = useQueryClient();
  const [awaitingCode, setAwaitingCode] = useState(false);
  const [code, setCode] = useState("");

  const statusQ = useQuery({
    queryKey: ["profile-2fa"],
    queryFn: () => api.twoFAStatus(),
  });
  const enabled = statusQ.data?.enabled ?? false;

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["profile-2fa"] });
    qc.invalidateQueries({ queryKey: ["profile"] });
  };

  const enroll = useMutation({
    mutationFn: () => api.twoFAEnroll(),
    onSuccess: () => {
      setAwaitingCode(true);
      setCode("");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't start email two-factor setup.")),
  });

  const verify = useMutation({
    mutationFn: (c: string) => api.twoFAEnrollVerify(c),
    onSuccess: () => {
      setAwaitingCode(false);
      setCode("");
      invalidate();
      notify("ok", "Email two-factor authentication is on.");
    },
    onError: (err) => notify("error", errMsg(err, "That code didn't verify. Try the current one.")),
  });

  const disable = useMutation({
    mutationFn: () => api.twoFADisable(),
    onSuccess: () => {
      setAwaitingCode(false);
      setCode("");
      invalidate();
      notify("ok", "Email two-factor authentication is off.");
    },
    onError: (err) => notify("error", errMsg(err, "Couldn't turn off two-factor authentication.")),
  });

  function onVerify(e: FormEvent) {
    e.preventDefault();
    verify.mutate(code.trim());
  }

  return (
    <section className={`card ${styles.panel}`}>
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Two-factor authentication</h2>
          <span className={styles.panelNote}>Get a one-time code by email on top of your password.</span>
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
            Email 2FA is on. You'll be emailed a 6-digit code when you sign in from a device you
            haven't trusted. Turning it off also signs out all of your trusted devices.
          </p>
          <div className={styles.actions}>
            <button className="btn btn-ghost" onClick={() => disable.mutate()} disabled={disable.isPending}>
              {disable.isPending ? "Turning off…" : "Turn off"}
            </button>
          </div>
        </div>
      ) : awaitingCode ? (
        <form className={styles.stack} onSubmit={onVerify}>
          <p className={styles.note}>We emailed a 6-digit code to your address. Enter it below to finish.</p>
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
                setAwaitingCode(false);
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
            Email 2FA is off. Turn it on to require a one-time email code at sign-in.
          </p>
          <div className={styles.actions}>
            <button className="btn btn-accent" onClick={() => enroll.mutate()} disabled={enroll.isPending}>
              {enroll.isPending ? "Sending code…" : "Enable email 2FA"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

/* ---- Trusted devices: list + per-row / bulk revoke ---- */
function TrustedDevicesCard() {
  const qc = useQueryClient();
  const devicesQ = useQuery({
    queryKey: ["trusted-devices"],
    queryFn: () => api.listTrustedDevices(),
  });
  const revoke = useMutation({
    mutationFn: (id: number) => api.revokeTrustedDevice(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trusted-devices"] }),
  });
  const revokeOthers = useMutation({
    mutationFn: () => api.revokeOtherTrustedDevices(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trusted-devices"] }),
  });
  const devices = devicesQ.data ?? [];

  return (
    <section className={`card ${styles.panel}`}>
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Trusted devices</h2>
          <span className={styles.panelNote}>
            Devices that can skip the email code until they expire or are revoked.
          </span>
        </div>
      </div>

      {devicesQ.isLoading ? (
        <div className={styles.skeleton} style={{ height: 72, borderRadius: "var(--r-md)" }} />
      ) : devices.length === 0 ? (
        <p className={styles.note}>No trusted devices.</p>
      ) : (
        <ul className={styles.stack} style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {devices.map((d) => (
            <li key={d.id} className={styles.field}>
              <div className={styles.fieldValue}>{d.device_label}</div>
              <span className={styles.panelNote}>
                Last used {new Date(d.last_used_at).toLocaleString()} · Expires{" "}
                {new Date(d.expires_at).toLocaleDateString()}
              </span>
              <div className={styles.actions} style={{ justifyContent: "flex-start", marginTop: "var(--sp-2)" }}>
                <button className="btn btn-ghost" onClick={() => revoke.mutate(d.id)} disabled={revoke.isPending}>
                  Revoke
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {devices.length > 1 && (
        <div className={styles.actions}>
          <button
            className="btn btn-ghost"
            onClick={() => revokeOthers.mutate()}
            disabled={revokeOthers.isPending}
          >
            {revokeOthers.isPending ? "Revoking…" : "Revoke all other devices"}
          </button>
        </div>
      )}
    </section>
  );
}

/* ---- Signed-in devices (active sessions): list + per-row / bulk sign-out ---- */
function SignedInDevicesCard({ notify }: { notify: (k: "ok" | "error", m: string) => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["sessions"], queryFn: () => api.listSessions() });
  const revoke = useMutation({
    mutationFn: (id: number) => api.revokeSession(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sessions"] }); notify("ok", "Signed that device out."); },
    onError: (e) => notify("error", errMsg(e, "Couldn't sign out that device.")),
  });
  const revokeOthers = useMutation({
    mutationFn: () => api.revokeOtherSessions(),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sessions"] }); notify("ok", "Signed out your other devices."); },
    onError: (e) => notify("error", errMsg(e, "Couldn't sign out the other devices.")),
  });
  const sessions = q.data ?? [];

  return (
    <section className={`card ${styles.panel}`}>
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Signed-in devices</h2>
          <span className={styles.panelNote}>Devices currently signed in to your account. Sign out any you don't recognize.</span>
        </div>
      </div>
      {q.isLoading ? (
        <div className={styles.skeleton} style={{ height: 72, borderRadius: "var(--r-md)" }} />
      ) : sessions.length === 0 ? (
        <p className={styles.note}>No active sessions.</p>
      ) : (
        <ul className={styles.stack} style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {sessions.map((s) => (
            <li key={s.id} className={styles.field}>
              <div className={styles.fieldValue}>
                {s.device_label}{" "}
                {s.current && <span className={`${styles.badge} ${styles.badgeOn}`}><span className={styles.badgeDot} aria-hidden />This device</span>}
              </div>
              <span className={styles.panelNote}>
                {s.ip_address ? `${s.ip_address} · ` : ""}Last active {new Date(s.last_seen_at).toLocaleString()}
              </span>
              {!s.current && (
                <div className={styles.actions} style={{ justifyContent: "flex-start", marginTop: "var(--sp-2)" }}>
                  <button className="btn btn-ghost" onClick={() => revoke.mutate(s.id)} disabled={revoke.isPending}>Sign out</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {sessions.length > 1 && (
        <div className={styles.actions}>
          <button className="btn btn-ghost" onClick={() => revokeOthers.mutate()} disabled={revokeOthers.isPending}>
            {revokeOthers.isPending ? "Signing out…" : "Sign out all other devices"}
          </button>
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
