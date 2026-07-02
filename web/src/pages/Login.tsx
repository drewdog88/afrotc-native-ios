/* Sign-in screen. Left: the "ascent" hero (recruiting as a climb to commission).
   Right: the credential form, with a 2FA code field revealed only when the API
   reports it's required. On success, routes to the dashboard. */
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { STAGES } from "../lib/stages";
import { Insignia } from "../components/Insignia";
import styles from "./Login.module.css";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needs2fa, setNeeds2fa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password, needs2fa ? totp : undefined);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = String(err.message ?? "").toLowerCase();
        if (err.status === 401 && (msg.includes("2fa") || msg.includes("totp") || msg.includes("code"))) {
          setNeeds2fa(true);
          setError("Enter your 6-digit authentication code to continue.");
        } else {
          setError(err.message || "Sign-in failed. Check your credentials.");
        }
      } else {
        setError("Unable to reach the server. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  // Bars climb in height toward the commissioning beacon.
  const rungHeights = [70, 108, 150, 196, 250];

  return (
    <div className={styles.wrap}>
      <section className={styles.hero}>
        <div className={styles.heroTop}>
          <Insignia size={30} />
          <div>
            <div className={styles.heroWord}>Detachment 695</div>
            <div className={styles.heroSub}>Air Force ROTC</div>
          </div>
        </div>

        <div className={styles.heroBody}>
          <div className={styles.heroKicker}>Recruiting Operations</div>
          <h1 className={styles.heroTitle}>Every recruit is a climb to commission.</h1>
          <p className={styles.heroText}>
            Track each prospect through the ascent — lead to commissioned — and watch the
            detachment's momentum change over time.
          </p>
        </div>

        <div className={styles.ladder} aria-hidden="true">
          {STAGES.map((s, i) => (
            <div
              key={s.key}
              className={styles.rung}
              style={{ height: rungHeights[i], background: s.color }}
            />
          ))}
        </div>

        <div className={styles.heroFoot}>AUTHORIZED PERSONNEL · DET 695 · USAF</div>
      </section>

      <section className={styles.panel}>
        <form className={styles.form} onSubmit={onSubmit}>
          <h2 className={styles.formTitle}>Sign in</h2>
          <p className={styles.formLede}>Access the detachment recruiting dashboard.</p>

          {error && <div className={styles.error}>{error}</div>}

          <div className={styles.group}>
            <label className="field-label" htmlFor="username">Username or email</label>
            <input
              id="username"
              className="input"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className={styles.group}>
            <label className="field-label" htmlFor="password">Password</label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {needs2fa && (
            <div className={styles.group}>
              <label className="field-label" htmlFor="totp">Authentication code</label>
              <input
                id="totp"
                className="input mono"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="123 456"
                value={totp}
                onChange={(e) => setTotp(e.target.value)}
                required
              />
            </div>
          )}

          <button className={`btn btn-primary ${styles.submit}`} type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <p className={styles.hint}>Trouble signing in? Contact a detachment administrator.</p>
        </form>
      </section>
    </div>
  );
}
