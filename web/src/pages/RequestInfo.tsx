/* Public "Request Information" page — the only unauthenticated data-entry surface.
   Creates a recruiting lead via POST /intake. Protected by Cloudflare Turnstile. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, type IntakeOptions } from "../lib/api";
import { Insignia } from "../components/Insignia";
import styles from "./RequestInfo.module.css";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? "1x00000000000000000000AA";

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, opts: { sitekey: string; callback: (t: string) => void; "error-callback"?: () => void }) => string;
      reset: (id?: string) => void;
    };
  }
}

export function RequestInfo() {
  const [options, setOptions] = useState<IntakeOptions | null>(null);
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", phone: "", current_school: "",
    grade_level: "", intended_entry_term: "fall", intended_entry_year: new Date().getFullYear() + 1,
    consent: false,
  });
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const widgetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.intakeOptions().then(setOptions).catch(() => setError("Couldn't load the form. Please refresh."));
  }, []);

  // Inject the Turnstile script once, then render the widget.
  useEffect(() => {
    const id = "cf-turnstile-script";
    function renderWidget() {
      if (window.turnstile && widgetRef.current && !widgetRef.current.hasChildNodes()) {
        window.turnstile.render(widgetRef.current, {
          sitekey: SITE_KEY,
          callback: setToken,
          "error-callback": () => setToken(""),
        });
      }
    }
    if (document.getElementById(id)) { renderWidget(); return; }
    const s = document.createElement("script");
    s.id = id;
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
    s.async = true;
    s.onload = renderWidget;
    document.head.appendChild(s);
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.consent) { setError("Please confirm you agree to be contacted."); return; }
    setBusy(true);
    try {
      await api.submitIntake({ ...form, turnstile_token: token } as never);
      setDone(true);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setError(msg);
      window.turnstile?.reset();
      setToken("");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className={styles.wrap}>
        <div className={styles.card}>
          <Insignia size={40} />
          <h1 className={styles.title}>Thank you!</h1>
          <p className={styles.lede}>We received your information. A Detachment 695 recruiter will reach out soon.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.card} onSubmit={onSubmit}>
        <div className={styles.head}>
          <Insignia size={40} />
          <div>
            <h1 className={styles.title}>Request Information</h1>
            <p className={styles.lede}>Interested in Air Force ROTC at Detachment 695? Tell us about yourself.</p>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.row}>
          <Field label="First name" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} required />
          <Field label="Last name" value={form.last_name} onChange={(v) => setForm({ ...form, last_name: v })} required />
        </div>
        <Field label="Email" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} required />
        <Field label="Phone" type="tel" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} required />
        <Field label="Current school" value={form.current_school} onChange={(v) => setForm({ ...form, current_school: v })} required />

        <div className={styles.group}>
          <label className="field-label" htmlFor="grade">Grade / year</label>
          <select id="grade" className="input" required value={form.grade_level}
                  onChange={(e) => setForm({ ...form, grade_level: e.target.value })}>
            <option value="" disabled>Select…</option>
            {options?.grade_levels.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className={styles.row}>
          <div className={styles.group}>
            <label className="field-label" htmlFor="term">Intended start term</label>
            <select id="term" className="input" value={form.intended_entry_term}
                    onChange={(e) => setForm({ ...form, intended_entry_term: e.target.value })}>
              {options?.terms.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className={styles.group}>
            <label className="field-label" htmlFor="year">Year</label>
            <input id="year" className="input" type="number" min={2000} max={2100} value={form.intended_entry_year}
                   onChange={(e) => setForm({ ...form, intended_entry_year: Number(e.target.value) })} required />
          </div>
        </div>

        <label className={styles.consent}>
          <input type="checkbox" checked={form.consent}
                 onChange={(e) => setForm({ ...form, consent: e.target.checked })} />
          <span>I agree to be contacted by phone, text, or email about AFROTC Detachment 695.</span>
        </label>

        <div ref={widgetRef} className={styles.turnstile} />

        <button className={`btn btn-primary ${styles.submit}`} type="submit" disabled={busy}>
          {busy ? "Submitting…" : "Submit"}
        </button>
      </form>
    </div>
  );
}

function Field(props: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) {
  const id = props.label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={styles.group}>
      <label className="field-label" htmlFor={id}>{props.label}</label>
      <input id={id} className="input" type={props.type ?? "text"} value={props.value}
             required={props.required} onChange={(e) => props.onChange(e.target.value)} />
    </div>
  );
}
