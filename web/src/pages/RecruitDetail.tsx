/* Recruit detail — view/edit a prospect and advance their pipeline stage. Advancing
   the stage POSTs to /recruits/{id}/stage, which appends an immutable RecruitStageEvent;
   that log is what the dashboard funnel + trend graphs are computed from, so this screen
   is where the mandatory "recruitment change over time" reporting actually gets its data.
   The stage-history timeline below reads those same events back. */
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  ApiError,
  type RecruitOut,
  type RecruitUpdate,
  type StageChange,
  type StageEventOut,
} from "../lib/api";
import { STAGES, DECLINED, stageMeta } from "../lib/stages";
import { StageChip } from "../components/StageChip";
import styles from "./RecruitDetail.module.css";

const ALL_STAGES = [...STAGES, DECLINED];

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) +
    " · " + d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function RecruitDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const recruitQ = useQuery({
    queryKey: ["recruit", id],
    queryFn: () => api.get<RecruitOut>(`/recruits/${id}`),
    enabled: !!id,
  });
  const historyQ = useQuery({
    queryKey: ["recruit-history", id],
    queryFn: () => api.get<StageEventOut[]>(`/recruits/${id}/stage-history`),
    enabled: !!id,
  });

  const recruit = recruitQ.data;

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["recruit", id] });
    qc.invalidateQueries({ queryKey: ["recruit-history", id] });
    qc.invalidateQueries({ queryKey: ["recruits"] });
    qc.invalidateQueries({ queryKey: ["funnel"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const [note, setNote] = useState("");
  const advance = useMutation({
    mutationFn: (to_stage: string) =>
      api.post(`/recruits/${id}/stage`, { to_stage, note: note.trim() || null } as StageChange),
    onSuccess: () => {
      setNote("");
      invalidateAll();
    },
  });

  if (recruitQ.isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.skeleton} style={{ height: 48, width: 280 }} />
        <div className={styles.grid}>
          <div className={styles.skeleton} style={{ height: 320 }} />
          <div className={styles.skeleton} style={{ height: 320 }} />
        </div>
      </div>
    );
  }

  if (recruitQ.isError || !recruit) {
    return (
      <div className={styles.page}>
        <button className={styles.back} onClick={() => navigate("/recruits")}>← Back to recruits</button>
        <div className={styles.formError}>Couldn't load this recruit. They may have been removed.</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <button className={styles.back} onClick={() => navigate("/recruits")}>← Back to recruits</button>

      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>{recruit.full_name}</h1>
          <div className={styles.headMeta}>
            <StageChip stage={recruit.stage} />
            {recruit.current_school && <span className={styles.empty}>{recruit.current_school}</span>}
          </div>
        </div>
      </div>

      <div className={styles.grid}>
        {/* Left: stage control + editable profile */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>
          <section className={`card ${styles.panel}`}>
            <h2 className={styles.panelTitle}>Advance stage</h2>
            <p className={styles.empty}>Move this recruit along the ascent. Each move is logged and feeds the funnel.</p>
            <div className={styles.stageRow}>
              {ALL_STAGES.map((s) => {
                const isCurrent = s.key === recruit.stage;
                return (
                  <button
                    key={s.key}
                    className={`${styles.stageBtn} ${isCurrent ? styles.stageBtnCurrent : ""}`}
                    disabled={isCurrent || advance.isPending}
                    onClick={() => advance.mutate(s.key)}
                    title={s.blurb}
                  >
                    <span className={styles.stageDot} style={{ background: s.color }} aria-hidden />
                    {s.label}
                  </button>
                );
              })}
            </div>
            <textarea
              className={styles.noteInput}
              placeholder="Add a note for this transition (optional)…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            {advance.isError && (
              <div className={styles.formError}>
                {advance.error instanceof ApiError ? advance.error.message : "Couldn't change the stage."}
              </div>
            )}
          </section>

          <ProfilePanel recruit={recruit} onSaved={invalidateAll} />
        </div>

        {/* Right: stage-history timeline */}
        <section className={`card ${styles.panel}`}>
          <h2 className={styles.panelTitle}>Stage history</h2>
          {historyQ.isLoading ? (
            <div className={styles.skeleton} style={{ height: 200 }} />
          ) : !historyQ.data || historyQ.data.length === 0 ? (
            <p className={styles.empty}>No stage changes recorded yet.</p>
          ) : (
            <div className={styles.timeline}>
              {[...historyQ.data]
                .sort((a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime())
                .map((ev, idx, arr) => {
                  const meta = stageMeta(ev.to_stage);
                  const from = ev.from_stage ? stageMeta(ev.from_stage).label : null;
                  return (
                    <div key={ev.id} className={styles.event}>
                      <div className={styles.rail}>
                        <span className={styles.railDot} style={{ background: meta.color }} />
                        {idx < arr.length - 1 && <span className={styles.railLine} />}
                      </div>
                      <div className={styles.eventBody}>
                        <div className={styles.eventTitle}>
                          {from ? <>{from} → <b>{meta.label}</b></> : <>Entered as <b>{meta.label}</b></>}
                        </div>
                        <div className={styles.eventTime}>{fmtDate(ev.changed_at)}</div>
                        {ev.note && <div className={styles.eventNote}>{ev.note}</div>}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function ProfilePanel({ recruit, onSaved }: { recruit: RecruitOut; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    first_name: recruit.first_name,
    last_name: recruit.last_name,
    email: recruit.email ?? "",
    phone: recruit.phone ?? "",
    current_school: recruit.current_school,
    school_type: recruit.school_type,
    major: recruit.major ?? "",
    notes: recruit.notes ?? "",
  });

  // Keep the form in sync if the recruit refetches while not editing.
  useEffect(() => {
    if (!editing) {
      setForm({
        first_name: recruit.first_name,
        last_name: recruit.last_name,
        email: recruit.email ?? "",
        phone: recruit.phone ?? "",
        current_school: recruit.current_school,
        school_type: recruit.school_type,
        major: recruit.major ?? "",
        notes: recruit.notes ?? "",
      });
    }
  }, [recruit, editing]);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: (body: RecruitUpdate) => api.patch<RecruitOut>(`/recruits/${recruit.id}`, body),
    onSuccess: () => {
      setEditing(false);
      onSaved();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save changes."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    save.mutate({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      current_school: form.current_school.trim(),
      school_type: form.school_type as RecruitUpdate["school_type"],
      major: form.major.trim() || null,
      notes: form.notes.trim() || null,
    });
  }

  if (!editing) {
    return (
      <section className={`card ${styles.panel}`}>
        <div className={styles.head}>
          <h2 className={styles.panelTitle}>Profile</h2>
          <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>
        </div>
        <div className={styles.fields}>
          <Field label="Email" value={recruit.email} />
          <Field label="Phone" value={recruit.phone} />
          <Field label="School" value={recruit.current_school} />
          <Field label="Type" value={recruit.school_type === "high_school" ? "High school" : recruit.school_type === "college" ? "College" : recruit.school_type} />
          <Field label="Major" value={recruit.major} />
          <Field label="GPA" value={recruit.gpa != null ? String(recruit.gpa) : null} />
          <div className={styles.fieldFull}>
            <div className={styles.fieldLabel}>Notes</div>
            <div className={styles.fieldValue}>{recruit.notes || <span className={styles.empty}>—</span>}</div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <form className={`card ${styles.panel}`} onSubmit={onSubmit}>
      <div className={styles.head}>
        <h2 className={styles.panelTitle}>Edit profile</h2>
      </div>
      {error && <div className={styles.formError}>{error}</div>}
      <div className={styles.fields}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="first_name">First name</label>
          <input id="first_name" className="input" value={form.first_name} onChange={set("first_name")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="last_name">Last name</label>
          <input id="last_name" className="input" value={form.last_name} onChange={set("last_name")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="email">Email</label>
          <input id="email" className="input" type="email" value={form.email} onChange={set("email")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="phone">Phone</label>
          <input id="phone" className="input" value={form.phone} onChange={set("phone")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="current_school">School</label>
          <input id="current_school" className="input" value={form.current_school} onChange={set("current_school")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="school_type">Type</label>
          <select id="school_type" className={styles.select} value={form.school_type} onChange={set("school_type")}>
            <option value="high_school">High school</option>
            <option value="college">College</option>
          </select>
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="major">Major</label>
          <input id="major" className="input" value={form.major} onChange={set("major")} />
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label className="field-label" htmlFor="notes">Notes</label>
          <textarea id="notes" className={styles.noteInput} value={form.notes} onChange={set("notes")} />
        </div>
      </div>
      <div style={{ display: "flex", gap: "var(--sp-3)" }}>
        <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
        <button type="submit" className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldLabel}>{label}</div>
      <div className={styles.fieldValue}>{value || <span className={styles.empty}>—</span>}</div>
    </div>
  );
}
