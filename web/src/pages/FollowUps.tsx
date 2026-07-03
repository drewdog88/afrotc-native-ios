/* Follow-ups — the recruiter's task queue. Every open follow-up is grouped by urgency
   (Overdue / Today / Upcoming) so nothing slips, with a Done archive below. Completing,
   creating, or deleting a follow-up updates the "open follow-ups" tile on the dashboard.
   Follow-ups can be linked to a recruit so a task always has context. */
import { useMemo, useState, type FormEvent } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./FollowUps.module.css";

type FollowUpOut = components["schemas"]["FollowUpOut"];
type FollowUpCreate = components["schemas"]["FollowUpCreate"];
type FollowUpUpdate = components["schemas"]["FollowUpUpdate"];
type FollowUpPage = components["schemas"]["Page_FollowUpOut_"];
type RecruitOut = components["schemas"]["RecruitOut"];
type RecruitPage = components["schemas"]["Page_RecruitOut_"];

type Bucket = "overdue" | "today" | "upcoming";

const GROUPS: { key: Bucket; label: string; empty: string }[] = [
  { key: "overdue", label: "Overdue", empty: "Nothing past due — you're caught up." },
  { key: "today", label: "Today", empty: "Nothing due today." },
  { key: "upcoming", label: "Upcoming", empty: "No upcoming follow-ups scheduled." },
];

function startOfToday(): number {
  const n = new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate()).getTime();
}

function bucketFor(due: string): Bucket {
  const d = new Date(due).getTime();
  const start = startOfToday();
  const end = start + 24 * 60 * 60 * 1000;
  if (d < start) return "overdue";
  if (d < end) return "today";
  return "upcoming";
}

function fmtDue(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return (
    d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) +
    " · " +
    d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
  );
}

function relativeDue(iso: string): string {
  const d = new Date(iso).getTime();
  const start = startOfToday();
  const dayMs = 24 * 60 * 60 * 1000;
  const diffDays = Math.round((new Date(d).setHours(0, 0, 0, 0) - start) / dayMs);
  if (diffDays === 0) return "today";
  if (diffDays === 1) return "tomorrow";
  if (diffDays === -1) return "yesterday";
  if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`;
  return `in ${diffDays} days`;
}

// datetime-local default: today at 5pm, formatted for the input's expected value.
function defaultDueLocal(): string {
  const n = new Date();
  n.setHours(17, 0, 0, 0);
  const pad = (x: number) => String(x).padStart(2, "0");
  return `${n.getFullYear()}-${pad(n.getMonth() + 1)}-${pad(n.getDate())}T${pad(n.getHours())}:${pad(n.getMinutes())}`;
}

export function FollowUps() {
  const qc = useQueryClient();
  const { canWrite } = useAuth();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<FollowUpOut | null>(null);

  const listQ = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<FollowUpPage>("/followups?limit=200"),
    placeholderData: keepPreviousData,
  });

  // Recruit names for the "linked to" chips + the create picker.
  const recruitsQ = useQuery({
    queryKey: ["recruits"],
    queryFn: () => api.get<RecruitPage>("/recruits?limit=200"),
    placeholderData: keepPreviousData,
  });

  const recruitName = useMemo(() => {
    const map = new Map<number, string>();
    for (const r of recruitsQ.data?.items ?? []) map.set(r.id, r.full_name);
    return map;
  }, [recruitsQ.data]);

  const items = listQ.data?.items ?? [];
  const open = items.filter((f) => f.status !== "done");
  const done = items.filter((f) => f.status === "done");

  const grouped: Record<Bucket, FollowUpOut[]> = { overdue: [], today: [], upcoming: [] };
  for (const f of open) grouped[bucketFor(f.due_date)].push(f);
  for (const b of Object.keys(grouped) as Bucket[]) {
    grouped[b].sort((a, c) => new Date(a.due_date).getTime() - new Date(c.due_date).getTime());
  }
  const doneSorted = [...done].sort(
    (a, c) => new Date(c.completed_at ?? c.due_date).getTime() - new Date(a.completed_at ?? a.due_date).getTime(),
  );

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["followups"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const hasAny = items.length > 0;
  const overdueCount = grouped.overdue.length;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Follow-ups</h1>
          <p className={styles.subtitle}>
            Your recruiting task queue — sorted by what needs attention first.
          </p>
        </div>
        {canWrite && (
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            New follow-up
          </button>
        )}
      </div>

      {overdueCount > 0 && (
        <div className={styles.banner}>
          <span className={styles.bannerDot} aria-hidden />
          {overdueCount} follow-up{overdueCount === 1 ? "" : "s"} past due — knock these out first.
        </div>
      )}

      {listQ.isLoading ? (
        <div className={styles.groups}>
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className={styles.skeleton} style={{ height: 160 }} />
          ))}
        </div>
      ) : listQ.isError ? (
        <div className={styles.formError}>Couldn't load follow-ups. Check that the API is running.</div>
      ) : !hasAny ? (
        <div className={`card ${styles.emptyState}`}>
          <div className={styles.emptyTitle}>No follow-ups yet</div>
          <p className={styles.emptyBody}>
            Follow-ups keep every recruit moving. Schedule a call, an email, or a check-in and it
            shows up here the moment it's due.
          </p>
          {canWrite && (
            <button className="btn btn-primary" onClick={() => setCreating(true)}>
              New follow-up
            </button>
          )}
        </div>
      ) : (
        <div className={styles.groups}>
          {GROUPS.map((g) => (
            <Group
              key={g.key}
              label={g.label}
              bucket={g.key}
              rows={grouped[g.key]}
              emptyCopy={g.empty}
              recruitName={recruitName}
              onChanged={invalidate}
              onEdit={setEditing}
              canWrite={canWrite}
            />
          ))}

          {doneSorted.length > 0 && (
            <Group
              label="Done"
              bucket="done"
              rows={doneSorted}
              emptyCopy=""
              recruitName={recruitName}
              onChanged={invalidate}
              onEdit={setEditing}
              canWrite={canWrite}
            />
          )}
        </div>
      )}

      {creating && (
        <CreateDrawer
          recruits={recruitsQ.data?.items ?? []}
          onClose={() => setCreating(false)}
          onCreated={invalidate}
        />
      )}

      {editing && (
        <EditDrawer
          followup={editing}
          recruits={recruitsQ.data?.items ?? []}
          onClose={() => setEditing(null)}
          onUpdated={invalidate}
        />
      )}
    </div>
  );
}

function Group({
  label,
  bucket,
  rows,
  emptyCopy,
  recruitName,
  onChanged,
  onEdit,
  canWrite,
}: {
  label: string;
  bucket: Bucket | "done";
  rows: FollowUpOut[];
  emptyCopy: string;
  recruitName: Map<number, string>;
  onChanged: () => void;
  onEdit: (followup: FollowUpOut) => void;
  canWrite: boolean;
}) {
  // Upcoming/Done empty groups stay hidden to keep the queue tight; Overdue/Today
  // always render so the recruiter sees an explicit "you're clear" signal.
  if (rows.length === 0 && (bucket === "upcoming" || bucket === "done")) return null;

  return (
    <section className={styles.group}>
      <div className={styles.groupHead}>
        <span className={`eyebrow ${bucket === "overdue" ? styles.overdueLabel : ""}`}>{label}</span>
        <span className={styles.groupCount}>{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <div className={`card ${styles.groupEmpty}`}>{emptyCopy}</div>
      ) : (
        <ul className={`card ${styles.list}`}>
          {rows.map((f) => (
            <Row key={f.id} followup={f} bucket={bucket} recruitName={recruitName} onChanged={onChanged} onEdit={onEdit} canWrite={canWrite} />
          ))}
        </ul>
      )}
    </section>
  );
}

function Row({
  followup,
  bucket,
  recruitName,
  onChanged,
  onEdit,
  canWrite,
}: {
  followup: FollowUpOut;
  bucket: Bucket | "done";
  recruitName: Map<number, string>;
  onChanged: () => void;
  onEdit: (followup: FollowUpOut) => void;
  canWrite: boolean;
}) {
  const isDone = followup.status === "done";

  const mutate = useMutation({
    mutationFn: async (action: "complete" | "reopen" | "delete") => {
      if (action === "complete") return api.post<FollowUpOut>(`/followups/${followup.id}/complete`);
      if (action === "reopen")
        return api.patch<FollowUpOut>(`/followups/${followup.id}`, { status: "open" } as FollowUpUpdate);
      return api.del(`/followups/${followup.id}`);
    },
    onSuccess: onChanged,
  });

  // Optimistic-feeling: while a mutation is in flight, keep the click stable.
  const busy = mutate.isPending;
  const linkedName = followup.recruit_id != null ? recruitName.get(followup.recruit_id) : undefined;

  return (
    <li className={`${styles.row} ${isDone ? styles.rowDone : ""}`}>
      {canWrite && (
        <button
          type="button"
          className={`${styles.check} ${isDone ? styles.checkDone : ""} ${
            bucket === "overdue" ? styles.checkOverdue : ""
          }`}
          aria-label={isDone ? "Reopen follow-up" : "Mark follow-up done"}
          aria-pressed={isDone}
          disabled={busy}
          onClick={() => mutate.mutate(isDone ? "reopen" : "complete")}
        >
          {isDone && (
            <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden>
              <path
                d="M3 8.5l3.2 3.2L13 4.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      )}

      <div className={styles.rowBody}>
        <div className={styles.note}>{followup.note}</div>
        <div className={styles.meta}>
          <span
            className={`${styles.due} ${bucket === "overdue" ? styles.dueOverdue : ""}`}
            title={fmtDue(followup.due_date)}
          >
            {isDone
              ? `Completed ${followup.completed_at ? fmtDue(followup.completed_at) : "—"}`
              : `Due ${fmtDue(followup.due_date)} · ${relativeDue(followup.due_date)}`}
          </span>
          {followup.recruit_id != null && (
            <Link
              to={`/recruits/${followup.recruit_id}`}
              className={styles.linked}
              title="Linked recruit"
              onClick={(e) => e.stopPropagation()}
            >
              <span className={styles.linkDot} aria-hidden />
              {linkedName ?? `Recruit #${followup.recruit_id}`}
            </Link>
          )}
        </div>
      </div>

      {canWrite && (
        <>
          <button
            type="button"
            className={styles.edit}
            aria-label="Edit follow-up"
            disabled={busy}
            onClick={() => onEdit(followup)}
          >
            Edit
          </button>

          <button
            type="button"
            className={styles.delete}
            aria-label="Delete follow-up"
            disabled={busy}
            onClick={() => mutate.mutate("delete")}
          >
            Delete
          </button>
        </>
      )}
    </li>
  );
}

function CreateDrawer({
  recruits,
  onClose,
  onCreated,
}: {
  recruits: RecruitOut[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [note, setNote] = useState("");
  const [due, setDue] = useState(defaultDueLocal());
  const [recruitId, setRecruitId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: FollowUpCreate) => api.post<FollowUpOut>("/followups", body),
    onSuccess: () => {
      onCreated();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't create the follow-up."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const trimmed = note.trim();
    if (!trimmed) {
      setError("Add a short note describing the task.");
      return;
    }
    const parsed = new Date(due);
    if (Number.isNaN(parsed.getTime())) {
      setError("Pick a valid due date.");
      return;
    }
    create.mutate({
      note: trimmed,
      due_date: parsed.toISOString(),
      status: "open",
      recruit_id: recruitId ? Number(recruitId) : null,
    });
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>New follow-up</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.field}>
          <label className="field-label" htmlFor="fu-note">
            What needs to happen?
          </label>
          <textarea
            id="fu-note"
            className={styles.noteInput}
            placeholder="Call to confirm application status, send scholarship packet…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="fu-due">
            Due
          </label>
          <input
            id="fu-due"
            className="input"
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
            required
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="fu-recruit">
            Linked recruit (optional)
          </label>
          <select
            id="fu-recruit"
            className={styles.select}
            value={recruitId}
            onChange={(e) => setRecruitId(e.target.value)}
          >
            <option value="">No recruit</option>
            {recruits.map((r) => (
              <option key={r.id} value={r.id}>
                {r.full_name}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create follow-up"}
          </button>
        </div>
      </form>
    </div>
  );
}

// Helper to format ISO date to datetime-local input value
function toDatetimeLocal(iso: string): string {
  const d = new Date(iso);
  const pad = (x: number) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function EditDrawer({
  followup,
  recruits,
  onClose,
  onUpdated,
}: {
  followup: FollowUpOut;
  recruits: RecruitOut[];
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [note, setNote] = useState(followup.note);
  const [due, setDue] = useState(toDatetimeLocal(followup.due_date));
  const [recruitId, setRecruitId] = useState(followup.recruit_id != null ? String(followup.recruit_id) : "");
  const [error, setError] = useState<string | null>(null);

  const update = useMutation({
    mutationFn: (body: FollowUpUpdate) => api.patch<FollowUpOut>(`/followups/${followup.id}`, body),
    onSuccess: () => {
      onUpdated();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't update the follow-up."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const trimmed = note.trim();
    if (!trimmed) {
      setError("Add a short note describing the task.");
      return;
    }
    const parsed = new Date(due);
    if (Number.isNaN(parsed.getTime())) {
      setError("Pick a valid due date.");
      return;
    }
    update.mutate({
      note: trimmed,
      due_date: parsed.toISOString(),
      recruit_id: recruitId ? Number(recruitId) : null,
    });
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Edit follow-up</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.field}>
          <label className="field-label" htmlFor="fu-edit-note">
            What needs to happen?
          </label>
          <textarea
            id="fu-edit-note"
            className={styles.noteInput}
            placeholder="Call to confirm application status, send scholarship packet…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="fu-edit-due">
            Due
          </label>
          <input
            id="fu-edit-due"
            className="input"
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
            required
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="fu-edit-recruit">
            Linked recruit (optional)
          </label>
          <select
            id="fu-edit-recruit"
            className={styles.select}
            value={recruitId}
            onChange={(e) => setRecruitId(e.target.value)}
          >
            <option value="">No recruit</option>
            {recruits.map((r) => (
              <option key={r.id} value={r.id}>
                {r.full_name}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
