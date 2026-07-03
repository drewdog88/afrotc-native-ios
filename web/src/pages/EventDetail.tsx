/* Event detail — view an event, edit its particulars in place, or remove it. Edits
   and deletes write back through /events/{id} and refresh the calendar list. If the
   event carries coordinates, we link out to a map rather than embed one. */
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./EventDetail.module.css";

type EventOut = components["schemas"]["EventOut"];
type EventUpdate = components["schemas"]["EventUpdate"];
type EventStatus = components["schemas"]["EventStatus"];

const STATUS_META: Record<string, { label: string; color: string }> = {
  scheduled: { label: "Scheduled", color: "var(--sky)" },
  completed: { label: "Completed", color: "var(--ok)" },
  cancelled: { label: "Cancelled", color: "var(--danger)" },
};
const STATUS_KEYS: EventStatus[] = ["scheduled", "completed", "cancelled"];

function statusMeta(key: string) {
  return STATUS_META[key] ?? { label: key, color: "var(--muted)" };
}
function parseYMD(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}
function fmtLongDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = parseYMD(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}
function fmtTime(t: string | null | undefined): string | null {
  if (!t) return null;
  const m = t.match(/(\d{1,2}):(\d{2})/);
  if (!m) return t;
  let h = Number(m[1]);
  const min = m[2];
  const ap = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${min} ${ap}`;
}
function timeRange(start?: string | null, end?: string | null): string | null {
  const s = fmtTime(start);
  const e = fmtTime(end);
  if (s && e) return `${s} – ${e}`;
  return s || e || null;
}

export function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { canWrite } = useAuth();

  const eventQ = useQuery({
    queryKey: ["event", id],
    queryFn: () => api.get<EventOut>(`/events/${id}`),
    enabled: !!id,
  });

  const event = eventQ.data;

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["event", id] });
    qc.invalidateQueries({ queryKey: ["events"] });
  };

  const del = useMutation({
    mutationFn: () => api.del(`/events/${id}`),
    onSuccess: () => {
      invalidateAll();
      navigate("/events");
    },
  });

  if (eventQ.isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.skeleton} style={{ height: 48, width: 280 }} />
        <div className={styles.grid}>
          <div className={styles.skeleton} style={{ height: 300 }} />
          <div className={styles.skeleton} style={{ height: 300 }} />
        </div>
      </div>
    );
  }

  if (eventQ.isError || !event) {
    return (
      <div className={styles.page}>
        <button className={styles.back} onClick={() => navigate("/events")}>← Back to events</button>
        <div className={styles.formError}>Couldn't load this event. It may have been removed.</div>
      </div>
    );
  }

  const meta = statusMeta(event.status);
  const range = timeRange(event.start_time, event.end_time);
  const hasCoords = event.latitude != null && event.longitude != null;

  return (
    <div className={styles.page}>
      <button className={styles.back} onClick={() => navigate("/events")}>← Back to events</button>

      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>{event.title}</h1>
          <div className={styles.headMeta}>
            <span className={styles.statusTag} style={{ color: meta.color }}>
              <span className={styles.statusDot} style={{ background: meta.color }} aria-hidden />
              {meta.label}
            </span>
            {event.event_type && <span className={styles.typeTag}>{event.event_type}</span>}
          </div>
        </div>
        {canWrite && (
          <button
            className="btn btn-ghost"
            onClick={() => {
              if (window.confirm("Remove this event? This can't be undone.")) del.mutate();
            }}
            disabled={del.isPending}
          >
            {del.isPending ? "Removing…" : "Delete"}
          </button>
        )}
      </div>

      {del.isError && (
        <div className={styles.formError}>
          {del.error instanceof ApiError ? del.error.message : "Couldn't delete this event."}
        </div>
      )}

      <div className={styles.grid}>
        <section className={`card ${styles.panel}`}>
          <div className={styles.whenRow}>
            <div className={styles.dateBlock}>
              <span className={styles.dateMonth}>{parseYMD(event.event_date).toLocaleDateString(undefined, { month: "short" })}</span>
              <span className={styles.dateDay}>{parseYMD(event.event_date).getDate()}</span>
            </div>
            <div>
              <div className={styles.whenDate}>{fmtLongDate(event.event_date)}</div>
              {range && <div className={styles.whenTime}>{range}</div>}
            </div>
          </div>

          <div className={styles.fields}>
            <Field label="Location" value={event.location} />
            <Field label="Attendees" value={event.attendees_count != null ? String(event.attendees_count) : null} />
            {hasCoords && (
              <div className={`${styles.field} ${styles.fieldFull}`}>
                <div className={styles.fieldLabel}>Coordinates</div>
                <div className={styles.fieldValue}>
                  <a
                    className={styles.mapLink}
                    href={`https://www.google.com/maps/search/?api=1&query=${event.latitude},${event.longitude}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {event.latitude?.toFixed(5)}, {event.longitude?.toFixed(5)} · Open map
                  </a>
                </div>
              </div>
            )}
            <div className={`${styles.field} ${styles.fieldFull}`}>
              <div className={styles.fieldLabel}>Description</div>
              <div className={styles.fieldValue}>{event.description || <span className={styles.empty}>—</span>}</div>
            </div>
            {event.notes && (
              <div className={`${styles.field} ${styles.fieldFull}`}>
                <div className={styles.fieldLabel}>Notes</div>
                <div className={styles.fieldValue}>{event.notes}</div>
              </div>
            )}
          </div>
        </section>

        {canWrite && <EditPanel event={event} onSaved={invalidateAll} />}
      </div>
    </div>
  );
}

function EditPanel({ event, onSaved }: { event: EventOut; onSaved: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: event.title,
    event_type: event.event_type,
    event_date: event.event_date,
    start_time: event.start_time ?? "",
    end_time: event.end_time ?? "",
    location: event.location ?? "",
    status: event.status,
    description: event.description ?? "",
    notes: event.notes ?? "",
    attendees_count: event.attendees_count != null ? String(event.attendees_count) : "0",
  });

  // Refetches (from another edit) shouldn't clobber an in-progress edit, but here the
  // form is always visible; resync when the underlying event identity/content changes.
  useEffect(() => {
    setForm({
      title: event.title,
      event_type: event.event_type,
      event_date: event.event_date,
      start_time: event.start_time ?? "",
      end_time: event.end_time ?? "",
      location: event.location ?? "",
      status: event.status,
      description: event.description ?? "",
      notes: event.notes ?? "",
      attendees_count: event.attendees_count != null ? String(event.attendees_count) : "0",
    });
  }, [event]);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: (body: EventUpdate) => api.patch<EventOut>(`/events/${event.id}`, body),
    onSuccess: () => onSaved(),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save changes."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const attendees = Number(form.attendees_count);
    save.mutate({
      title: form.title.trim(),
      event_type: form.event_type.trim() || null,
      event_date: form.event_date,
      start_time: form.start_time.trim() || null,
      end_time: form.end_time.trim() || null,
      location: form.location.trim() || null,
      status: form.status as EventStatus,
      description: form.description.trim() || null,
      notes: form.notes.trim() || null,
      attendees_count: Number.isFinite(attendees) ? attendees : 0,
    });
  }

  return (
    <form className={`card ${styles.panel}`} onSubmit={onSubmit}>
      <h2 className={styles.panelTitle}>Edit event</h2>
      {error && <div className={styles.formError}>{error}</div>}

      <div className={styles.field}>
        <label className="field-label" htmlFor="title">Title</label>
        <input id="title" className="input" value={form.title} onChange={set("title")} required />
      </div>

      <div className={styles.formRow}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="event_type">Type</label>
          <input id="event_type" className="input" value={form.event_type} onChange={set("event_type")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="status">Status</label>
          <select id="status" className={styles.select} value={form.status} onChange={set("status")}>
            {STATUS_KEYS.map((s) => (
              <option key={s} value={s}>{statusMeta(s).label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.formRow}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="event_date">Date</label>
          <input id="event_date" className="input" type="date" value={form.event_date} onChange={set("event_date")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="attendees_count">Attendees</label>
          <input id="attendees_count" className="input" type="number" min="0" value={form.attendees_count} onChange={set("attendees_count")} />
        </div>
      </div>

      <div className={styles.formRow}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="start_time">Start time</label>
          <input id="start_time" className="input" type="time" value={form.start_time} onChange={set("start_time")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="end_time">End time</label>
          <input id="end_time" className="input" type="time" value={form.end_time} onChange={set("end_time")} />
        </div>
      </div>

      <div className={styles.field}>
        <label className="field-label" htmlFor="location">Location</label>
        <input id="location" className="input" value={form.location} onChange={set("location")} />
      </div>

      <div className={styles.field}>
        <label className="field-label" htmlFor="description">Description</label>
        <textarea id="description" className={styles.textarea} value={form.description} onChange={set("description")} />
      </div>

      <div className={styles.field}>
        <label className="field-label" htmlFor="notes">Notes</label>
        <textarea id="notes" className={styles.textarea} value={form.notes} onChange={set("notes")} />
      </div>

      <div className={styles.actions}>
        <button type="submit" className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save changes"}
        </button>
        {save.isSuccess && !save.isPending && <span className={styles.saved}>Saved</span>}
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
