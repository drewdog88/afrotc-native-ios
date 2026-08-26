/* Non-blocking first-login nudge to turn on email 2FA. A dismissible strip at
   the top of the app — never grays out or traps the page. "Turn on" routes to
   Profile (where the themed toggle + code entry live); "Not now" dismisses for
   good. Shown once, only for a user who hasn't enabled 2FA and hasn't been
   prompted. */
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import styles from "./EnrollmentBanner.module.css";

export function EnrollmentBanner() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const dismiss = useMutation({
    mutationFn: () => api.twoFAEnrollmentDismiss(),
    onSuccess: () => { void refresh(); },
  });

  if (!user || user.two_factor_enabled || user.two_factor_enrollment_prompted) return null;

  return (
    <div className={styles.banner} role="region" aria-label="Two-factor setup">
      <span className={styles.text}>
        Add an email code at sign-in for extra security on your account.
      </span>
      <div className={styles.actions}>
        <button className="btn btn-ghost" onClick={() => dismiss.mutate()} disabled={dismiss.isPending}>
          {dismiss.isPending ? "Dismissing…" : "Not now"}
        </button>
        <button className="btn btn-primary" onClick={() => navigate("/profile")}>Turn on</button>
      </div>
    </div>
  );
}
