import { useEffect, useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError, api } from "../lib/api";
import { useAuth } from "../lib/auth";

type ChallengeState = { challengeToken?: string; method?: string };

export function LoginVerify() {
  const { completeVerify } = useAuth();
  const navigate = useNavigate();
  const state = (useLocation().state ?? {}) as ChallengeState;
  const challengeToken = state.challengeToken;

  const [code, setCode] = useState("");
  const [trustDevice, setTrustDevice] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!challengeToken) navigate("/login", { replace: true });
  }, [challengeToken, navigate]);

  useEffect(() => {
    if (cooldown <= 0) return;
    timer.current = window.setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [cooldown]);

  if (!challengeToken) return null;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await completeVerify(challengeToken as string, code.trim(), trustDevice);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Verification failed. Try again.";
      setError(msg || "Verification failed. Try again.");
      // If the challenge was invalidated (too many attempts), send them back.
      if (err instanceof ApiError && err.status === 400) {
        setTimeout(() => navigate("/login", { replace: true }), 1500);
      }
    } finally {
      setBusy(false);
    }
  }

  async function onResend() {
    setError(null);
    try {
      await api.loginResend(challengeToken as string);
      setCooldown(60);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend the code.");
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "10vh auto" }}>
      <h1>Enter your sign-in code</h1>
      <p className="muted">
        We emailed a 6-digit code to your address. It expires in 10 minutes.
      </p>
      <form onSubmit={onSubmit}>
        <label className="field-label" htmlFor="code">
          Verification code
        </label>
        <input
          id="code"
          className="input"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          autoFocus
        />
        <label style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <input
            type="checkbox"
            checked={trustDevice}
            onChange={(e) => setTrustDevice(e.target.checked)}
          />
          Trust this device for 30 days
        </label>
        {error && <div className="form-error">{error}</div>}
        <button className="btn btn-primary" type="submit" disabled={busy || code.length < 6}>
          {busy ? "Verifying…" : "Verify"}
        </button>
      </form>
      <button className="btn btn-ghost" onClick={onResend} disabled={cooldown > 0}>
        {cooldown > 0 ? `Resend code (${cooldown}s)` : "Resend code"}
      </button>
    </div>
  );
}
