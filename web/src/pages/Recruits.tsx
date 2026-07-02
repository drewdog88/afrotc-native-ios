/* Recruits roster — the operational heart of the pipeline. Search + stage-scope the
   roster, open a recruit to advance their stage (which writes the RecruitStageEvents
   that power the funnel/trend reporting), or add a new prospect. */
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type RecruitCreate, type RecruitOut, type RecruitPage } from "../lib/api";
import { STAGES, DECLINED, stageMeta } from "../lib/stages";
import { StageChip } from "../components/StageChip";
import styles from "./Recruits.module.css";

const ALL_STAGES = [...STAGES, DECLINED];

function schoolLabel(t: string | null | undefined): string {
  if (t === "high_school") return "High school";
  if (t === "college") return "College";
  return "—";
}

export function Recruits() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [stage, setStage] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const params = new URLSearchParams({ limit: "200" });
  if (search.trim()) params.set("search", search.trim());
  if (stage) params.set("stage", stage);

  const listQ = useQuery({
    queryKey: ["recruits", search.trim(), stage],
    queryFn: () => api.get<RecruitPage>(`/recruits?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const items = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Recruits</h1>
          <p className={styles.subtitle}>Every prospect in the pipeline — advance a recruit to move the funnel.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          Add recruit
        </button>
      </div>

      <div className={styles.toolbar}>
        <input
          className={`input ${styles.search}`}
          placeholder="Search by name, email, or school…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className={styles.filters}>
          <button
            className={`${styles.filterChip} ${stage === null ? styles.filterChipActive : ""}`}
            onClick={() => setStage(null)}
          >
            All
          </button>
          {ALL_STAGES.map((s) => (
            <button
              key={s.key}
              className={`${styles.filterChip} ${stage === s.key ? styles.filterChipActive : ""}`}
              onClick={() => setStage(stage === s.key ? null : s.key)}
            >
              <span className={styles.filterDot} style={{ background: s.color }} aria-hidden />
              {s.short}
            </button>
          ))}
        </div>
      </div>

      <section className={`card ${styles.tableWrap}`}>
        {listQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 320, margin: "var(--sp-4)" }} />
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            {search || stage ? "No recruits match this view." : "No recruits yet. Add your first prospect to get started."}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th className={styles.colHide}>School</th>
                <th className={styles.colHide}>Type</th>
                <th>Stage</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} className={styles.row} onClick={() => navigate(`/recruits/${r.id}`)}>
                  <td>
                    <div className={styles.name}>{r.full_name}</div>
                    {r.email && <div className={styles.sub}>{r.email}</div>}
                  </td>
                  <td className={styles.colHide}>{r.current_school || <span className={styles.muted}>—</span>}</td>
                  <td className={styles.colHide}>{schoolLabel(r.school_type)}</td>
                  <td>
                    <StageChip stage={r.stage} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {!listQ.isLoading && items.length > 0 && (
        <div className={styles.count}>
          {items.length}
          {total > items.length ? ` of ${total}` : ""} recruit{total === 1 ? "" : "s"}
        </div>
      )}

      {creating && <CreateDrawer onClose={() => setCreating(false)} />}
    </div>
  );
}

function CreateDrawer({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    current_school: "",
    school_type: "high_school",
    stage: "lead",
  });
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const create = useMutation({
    mutationFn: (body: RecruitCreate) => api.post<RecruitOut>("/recruits", body),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["recruits"] });
      qc.invalidateQueries({ queryKey: ["funnel"] });
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      navigate(`/recruits/${created.id}`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't create the recruit."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const body: RecruitCreate = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      current_school: form.current_school.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      school_type: form.school_type as RecruitCreate["school_type"],
      stage: form.stage as RecruitCreate["stage"],
    };
    create.mutate(body);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Add recruit</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label className="field-label" htmlFor="first_name">First name</label>
            <input id="first_name" className="input" value={form.first_name} onChange={set("first_name")} required autoFocus />
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="last_name">Last name</label>
            <input id="last_name" className="input" value={form.last_name} onChange={set("last_name")} required />
          </div>
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

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label className="field-label" htmlFor="school_type">School type</label>
            <select id="school_type" className={styles.select} value={form.school_type} onChange={set("school_type")}>
              <option value="high_school">High school</option>
              <option value="college">College</option>
            </select>
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="stage">Starting stage</label>
            <select id="stage" className={styles.select} value={form.stage} onChange={set("stage")}>
              {[...STAGES, DECLINED].map((s) => (
                <option key={s.key} value={s.key}>{stageMeta(s.key).label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add recruit"}
          </button>
        </div>
      </form>
    </div>
  );
}
