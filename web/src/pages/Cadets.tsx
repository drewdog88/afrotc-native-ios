/* Cadets roster — the enrolled corps behind the recruiting pipeline. Search and
   scope by status, open a cadet to edit their profile, or add a new cadet. Unlike
   recruits, cadets carry an enrollment status (active / inactive / graduated) with
   the unenrollment reason/date captured when someone goes inactive. */
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import type { components } from "../api/schema";
import styles from "./Cadets.module.css";

type CadetOut = components["schemas"]["CadetOut"];
type CadetCreate = components["schemas"]["CadetCreate"];
type CadetUpdate = components["schemas"]["CadetUpdate"];
type CadetPage = components["schemas"]["Page_CadetOut_"];

/* Enrollment status identity — local to this screen (not the stage ramp). Mirrors
   the backend CadetStatus enum (active / inactive / graduated). Green for the active
   corps, warning red for those who've gone inactive, gold for graduates. */
interface StatusMeta {
  key: string;
  label: string;
  color: string;
}
const STATUSES: StatusMeta[] = [
  { key: "active", label: "Active", color: "var(--ok)" },
  { key: "inactive", label: "Inactive", color: "var(--danger)" },
  { key: "graduated", label: "Graduated", color: "var(--accent)" },
];
function statusMeta(key: string): StatusMeta {
  return STATUSES.find((s) => s.key === key) ?? { key, label: key || "—", color: "var(--muted)" };
}

function StatusPill({ status }: { status: string }) {
  const meta = statusMeta(status);
  return (
    <span className={styles.pill}>
      <span className={styles.pillDot} style={{ background: meta.color }} aria-hidden />
      {meta.label}
    </span>
  );
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// type=date needs YYYY-MM-DD; trim any time component off a stored ISO string.
function toDateInput(iso: string | null | undefined): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

export function Cadets() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const params = new URLSearchParams({ limit: "200" });
  if (search.trim()) params.set("search", search.trim());
  if (status) params.set("status", status);

  const listQ = useQuery({
    queryKey: ["cadets", search.trim(), status],
    queryFn: () => api.get<CadetPage>(`/cadets?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const items = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Cadets</h1>
          <p className={styles.subtitle}>The enrolled corps — search the roster or add a cadet.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          Add cadet
        </button>
      </div>

      <div className={styles.toolbar}>
        <input
          className={`input ${styles.search}`}
          placeholder="Search by name, email, or major…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className={styles.filters}>
          <button
            className={`${styles.filterChip} ${status === null ? styles.filterChipActive : ""}`}
            onClick={() => setStatus(null)}
          >
            All
          </button>
          {STATUSES.map((s) => (
            <button
              key={s.key}
              className={`${styles.filterChip} ${status === s.key ? styles.filterChipActive : ""}`}
              onClick={() => setStatus(status === s.key ? null : s.key)}
            >
              <span className={styles.filterDot} style={{ background: s.color }} aria-hidden />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <section className={`card ${styles.tableWrap}`}>
        {listQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 320, margin: "var(--sp-4)" }} />
        ) : items.length === 0 ? (
          <div className={styles.emptyRow}>
            {search || status ? "No cadets match this view." : "No cadets yet. Add your first cadet to get started."}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th className={styles.colHide}>Rank</th>
                <th className={styles.colHide}>Major</th>
                <th className={styles.colHide}>Grad year</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className={styles.row} onClick={() => navigate(`/cadets/${c.id}`)}>
                  <td>
                    <div className={styles.name}>{c.full_name}</div>
                    {c.email && <div className={styles.sub}>{c.email}</div>}
                  </td>
                  <td className={styles.colHide}>{c.cadet_rank || <span className={styles.muted}>—</span>}</td>
                  <td className={styles.colHide}>{c.major || <span className={styles.muted}>—</span>}</td>
                  <td className={`${styles.colHide} mono`}>{c.graduation_year}</td>
                  <td>
                    <StatusPill status={c.status} />
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
          {total > items.length ? ` of ${total}` : ""} cadet{total === 1 ? "" : "s"}
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
    cadet_rank: "",
    major: "",
    graduation_year: String(new Date().getFullYear() + 4),
    gpa: "",
    hometown: "",
    officer_interest: "",
    status: "active",
  });
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const create = useMutation({
    mutationFn: (body: CadetCreate) => api.post<CadetOut>("/cadets", body),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["cadets"] });
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      navigate(`/cadets/${created.id}`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't create the cadet."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const gradYear = Number(form.graduation_year);
    if (!Number.isFinite(gradYear)) {
      setError("Enter a valid graduation year.");
      return;
    }
    const gpaNum = form.gpa.trim() ? Number(form.gpa) : null;
    if (gpaNum != null && !Number.isFinite(gpaNum)) {
      setError("Enter a valid GPA, or leave it blank.");
      return;
    }
    const body: CadetCreate = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      cadet_rank: form.cadet_rank.trim(),
      major: form.major.trim(),
      graduation_year: gradYear,
      gpa: gpaNum,
      hometown: form.hometown.trim() || null,
      officer_interest: form.officer_interest.trim() || null,
      status: form.status,
    };
    create.mutate(body);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Add cadet</h2>
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
          <input id="email" className="input" type="email" value={form.email} onChange={set("email")} required />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="phone">Phone</label>
          <input id="phone" className="input" value={form.phone} onChange={set("phone")} />
        </div>

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label className="field-label" htmlFor="cadet_rank">Rank</label>
            <input id="cadet_rank" className="input" value={form.cadet_rank} onChange={set("cadet_rank")} required />
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="graduation_year">Graduation year</label>
            <input id="graduation_year" className="input" type="number" inputMode="numeric" value={form.graduation_year} onChange={set("graduation_year")} required />
          </div>
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="major">Major</label>
          <input id="major" className="input" value={form.major} onChange={set("major")} required />
        </div>

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label className="field-label" htmlFor="gpa">GPA</label>
            <input id="gpa" className="input" type="number" step="0.01" inputMode="decimal" value={form.gpa} onChange={set("gpa")} />
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="status">Status</label>
            <select id="status" className={styles.select} value={form.status} onChange={set("status")}>
              {STATUSES.map((s) => (
                <option key={s.key} value={s.key}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="hometown">Hometown</label>
          <input id="hometown" className="input" value={form.hometown} onChange={set("hometown")} />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="officer_interest">Officer interest</label>
          <input id="officer_interest" className="input" value={form.officer_interest} onChange={set("officer_interest")} />
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add cadet"}
          </button>
        </div>
      </form>
    </div>
  );
}

export function CadetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const cadetQ = useQuery({
    queryKey: ["cadet", id],
    queryFn: () => api.get<CadetOut>(`/cadets/${id}`),
    enabled: !!id,
  });

  const cadet = cadetQ.data;

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["cadet", id] });
    qc.invalidateQueries({ queryKey: ["cadets"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const remove = useMutation({
    mutationFn: () => api.del(`/cadets/${id}`),
    onSuccess: () => {
      invalidateAll();
      navigate("/cadets");
    },
  });

  if (cadetQ.isLoading) {
    return (
      <div className={styles.detailPage}>
        <div className={styles.skeleton} style={{ height: 48, width: 280 }} />
        <div className={styles.skeleton} style={{ height: 360 }} />
      </div>
    );
  }

  if (cadetQ.isError || !cadet) {
    return (
      <div className={styles.detailPage}>
        <button className={styles.back} onClick={() => navigate("/cadets")}>← Back to cadets</button>
        <div className={styles.formError}>Couldn't load this cadet. They may have been removed.</div>
      </div>
    );
  }

  return (
    <div className={styles.detailPage}>
      <button className={styles.back} onClick={() => navigate("/cadets")}>← Back to cadets</button>

      <div className={styles.detailHead}>
        <div>
          <h1 className={styles.title}>{cadet.full_name}</h1>
          <div className={styles.headMeta}>
            <StatusPill status={cadet.status} />
            {cadet.cadet_rank && <span className={styles.empty}>{cadet.cadet_rank}</span>}
          </div>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => {
            if (window.confirm(`Remove ${cadet.full_name} from the roster? This can't be undone.`)) {
              remove.mutate();
            }
          }}
          disabled={remove.isPending}
        >
          {remove.isPending ? "Removing…" : "Remove"}
        </button>
      </div>

      {remove.isError && (
        <div className={styles.formError}>
          {remove.error instanceof ApiError ? remove.error.message : "Couldn't remove this cadet."}
        </div>
      )}

      <ProfilePanel cadet={cadet} onSaved={invalidateAll} />
    </div>
  );
}

function ProfilePanel({ cadet, onSaved }: { cadet: CadetOut; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const blank = () => ({
    first_name: cadet.first_name,
    last_name: cadet.last_name,
    email: cadet.email,
    phone: cadet.phone ?? "",
    cadet_rank: cadet.cadet_rank,
    major: cadet.major,
    graduation_year: String(cadet.graduation_year),
    gpa: cadet.gpa != null ? String(cadet.gpa) : "",
    hometown: cadet.hometown ?? "",
    officer_interest: cadet.officer_interest ?? "",
    status: cadet.status,
    unenrollment_reason: cadet.unenrollment_reason ?? "",
    unenrollment_date: toDateInput(cadet.unenrollment_date),
  });
  const [form, setForm] = useState(blank);

  // Keep the form in sync if the cadet refetches while not editing.
  useEffect(() => {
    if (!editing) setForm(blank());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cadet, editing]);

  const set = (k: keyof ReturnType<typeof blank>) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: (body: CadetUpdate) => api.patch<CadetOut>(`/cadets/${cadet.id}`, body),
    onSuccess: () => {
      setEditing(false);
      onSaved();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save changes."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const gradYear = Number(form.graduation_year);
    if (!Number.isFinite(gradYear)) {
      setError("Enter a valid graduation year.");
      return;
    }
    const gpaNum = form.gpa.trim() ? Number(form.gpa) : null;
    if (gpaNum != null && !Number.isFinite(gpaNum)) {
      setError("Enter a valid GPA, or leave it blank.");
      return;
    }
    const isInactive = form.status === "inactive";
    save.mutate({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      cadet_rank: form.cadet_rank.trim(),
      major: form.major.trim(),
      graduation_year: gradYear,
      gpa: gpaNum,
      hometown: form.hometown.trim() || null,
      officer_interest: form.officer_interest.trim() || null,
      status: form.status,
      // Clear the unenrollment fields unless the cadet is inactive.
      unenrollment_reason: isInactive ? form.unenrollment_reason.trim() || null : null,
      unenrollment_date: isInactive ? form.unenrollment_date || null : null,
    });
  }

  if (!editing) {
    const unenrolled = cadet.status === "inactive";
    return (
      <section className={`card ${styles.panel}`}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Profile</h2>
          <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>
        </div>
        <div className={styles.fields}>
          <Field label="Email" value={cadet.email} />
          <Field label="Phone" value={cadet.phone} />
          <Field label="Rank" value={cadet.cadet_rank} />
          <Field label="Major" value={cadet.major} />
          <Field label="Graduation year" value={String(cadet.graduation_year)} mono />
          <Field label="GPA" value={cadet.gpa != null ? String(cadet.gpa) : null} mono />
          <Field label="Hometown" value={cadet.hometown} />
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Status</div>
            <div className={styles.fieldValue}><StatusPill status={cadet.status} /></div>
          </div>
          <div className={styles.fieldFull}>
            <div className={styles.fieldLabel}>Officer interest</div>
            <div className={styles.fieldValue}>{cadet.officer_interest || <span className={styles.empty}>—</span>}</div>
          </div>
          {unenrolled && (
            <>
              <Field label="Unenrollment date" value={fmtDate(cadet.unenrollment_date)} mono />
              <div className={styles.fieldFull}>
                <div className={styles.fieldLabel}>Unenrollment reason</div>
                <div className={styles.fieldValue}>{cadet.unenrollment_reason || <span className={styles.empty}>—</span>}</div>
              </div>
            </>
          )}
        </div>
      </section>
    );
  }

  const isInactive = form.status === "inactive";
  return (
    <form className={`card ${styles.panel}`} onSubmit={onSubmit}>
      <div className={styles.panelHead}>
        <h2 className={styles.panelTitle}>Edit profile</h2>
      </div>
      {error && <div className={styles.formError}>{error}</div>}
      <div className={styles.fields}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_first_name">First name</label>
          <input id="e_first_name" className="input" value={form.first_name} onChange={set("first_name")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_last_name">Last name</label>
          <input id="e_last_name" className="input" value={form.last_name} onChange={set("last_name")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_email">Email</label>
          <input id="e_email" className="input" type="email" value={form.email} onChange={set("email")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_phone">Phone</label>
          <input id="e_phone" className="input" value={form.phone} onChange={set("phone")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_cadet_rank">Rank</label>
          <input id="e_cadet_rank" className="input" value={form.cadet_rank} onChange={set("cadet_rank")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_major">Major</label>
          <input id="e_major" className="input" value={form.major} onChange={set("major")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_graduation_year">Graduation year</label>
          <input id="e_graduation_year" className="input" type="number" inputMode="numeric" value={form.graduation_year} onChange={set("graduation_year")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_gpa">GPA</label>
          <input id="e_gpa" className="input" type="number" step="0.01" inputMode="decimal" value={form.gpa} onChange={set("gpa")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_hometown">Hometown</label>
          <input id="e_hometown" className="input" value={form.hometown} onChange={set("hometown")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_status">Status</label>
          <select id="e_status" className={styles.select} value={form.status} onChange={set("status")}>
            {STATUSES.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label className="field-label" htmlFor="e_officer_interest">Officer interest</label>
          <input id="e_officer_interest" className="input" value={form.officer_interest} onChange={set("officer_interest")} />
        </div>
        {isInactive && (
          <>
            <div className={styles.field}>
              <label className="field-label" htmlFor="e_unenrollment_date">Unenrollment date</label>
              <input id="e_unenrollment_date" className="input" type="date" value={form.unenrollment_date} onChange={set("unenrollment_date")} />
            </div>
            <div className={`${styles.field} ${styles.fieldFull}`}>
              <label className="field-label" htmlFor="e_unenrollment_reason">Unenrollment reason</label>
              <textarea id="e_unenrollment_reason" className={styles.noteInput} value={form.unenrollment_reason} onChange={set("unenrollment_reason")} placeholder="Why did this cadet leave the program?" />
            </div>
          </>
        )}
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

function Field({ label, value, mono }: { label: string; value: string | null | undefined; mono?: boolean }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldLabel}>{label}</div>
      <div className={`${styles.fieldValue} ${mono ? "mono" : ""}`}>{value || <span className={styles.empty}>—</span>}</div>
    </div>
  );
}
