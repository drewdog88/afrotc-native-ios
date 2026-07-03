/* Self-service password reset. No email: the user proves ownership by answering
   the security question stored on their account.
   Step 1 — enter username/email → the API returns that account's question.
   Step 2 — answer it and set a new password → back to sign in.
   Reuses the Login split-screen (hero + panel) for visual continuity. */
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { STAGES } from "../lib/stages";
import { Insignia } from "../components/Insignia";
import styles from "./Login.module.css";

type Step = "identify" | "answer" | "done";

export function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("identify");
  const [username, setUsername] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function fail(err: unknown, fallback: string) {
    if (err instanceof ApiError) setError(err.message || fallback);
    else setError("Unable to reach the server. Try again.");
  }

  async function onIdentify(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<{ secret_question: string }>("/auth/forgot-password", {
        username,
      });
      setQuestion(res.secret_question);
      setStep("answer");
    } catch (err) {
      fail(err, "We couldn't find an account for that username or email.");
    } finally {
      setBusy(false);
    }
  }

  async function onReset(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("The new password and confirmation don't match.");
      return;
    }
    if (password.length < 8) {
      setError("Use at least 8 characters for the new password.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", {
        username,
        secret_answer: answer,
        new_password: password,
      });
      setStep("done");
    } catch (err) {
      fail(err, "Couldn't reset your password. Check your answer and try again.");
    } finally {
      setBusy(false);
    }
  }

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
          <div className={styles.heroKicker}>Account Recovery</div>
          <h1 className={styles.heroTitle}>Back on the climb.</h1>
          <p className={styles.heroText}>
            Answer the security question you set up to reset your password — no email
            required. You'll be signing in again in a moment.
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
        {step === "identify" && (
          <form className={styles.form} onSubmit={onIdentify}>
            <h2 className={styles.formTitle}>Reset password</h2>
            <p className={styles.formLede}>Enter your username or email to begin.</p>

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

            <button className={`btn btn-primary ${styles.submit}`} type="submit" disabled={busy}>
              {busy ? "Checking…" : "Continue"}
            </button>

            <p className={styles.hint}>
              Remembered it? <Link to="/login">Back to sign in</Link>
            </p>
          </form>
        )}

        {step === "answer" && (
          <form className={styles.form} onSubmit={onReset}>
            <h2 className={styles.formTitle}>Security check</h2>
            <p className={styles.formLede}>Answer your question, then choose a new password.</p>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.group}>
              <label className="field-label">Your security question</label>
              <p className={styles.formLede} style={{ margin: 0 }}>{question}</p>
            </div>

            <div className={styles.group}>
              <label className="field-label" htmlFor="answer">Answer</label>
              <input
                id="answer"
                className="input"
                autoComplete="off"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className={styles.group}>
              <label className="field-label" htmlFor="new_password">New password</label>
              <input
                id="new_password"
                className="input"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <div className={styles.group}>
              <label className="field-label" htmlFor="confirm">Confirm new password</label>
              <input
                id="confirm"
                className="input"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </div>

            <button className={`btn btn-primary ${styles.submit}`} type="submit" disabled={busy}>
              {busy ? "Resetting…" : "Reset password"}
            </button>

            <p className={styles.hint}>
              <Link to="/login">Back to sign in</Link>
            </p>
          </form>
        )}

        {step === "done" && (
          <div className={styles.form}>
            <h2 className={styles.formTitle}>Password reset</h2>
            <p className={styles.formLede}>
              Your password has been updated and any lockout cleared. You can sign in now.
            </p>
            <button
              className={`btn btn-primary ${styles.submit}`}
              type="button"
              onClick={() => navigate("/login", { replace: true })}
            >
              Go to sign in
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
