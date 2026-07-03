/* Events + calendar — the detachment's outreach schedule. Flip between a month
   calendar (event dots on each day) and a chronological list of what's coming up,
   scope by status, and open any event to view or edit it. Adding an event drops it
   straight onto the calendar. Pure JS date math — no date library. */
import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./Events.module.css";

type EventOut = components["schemas"]["EventOut"];
type EventCreate = components["schemas"]["EventCreate"];
type EventPage = components["schemas"]["Page_EventOut_"];
type EventStatus = components["schemas"]["EventStatus"];

const STATUS_META: Record<string, { label: string; color: string }> = {
  scheduled: { label: "Scheduled", color: "var(--sky)" },
  completed: { label: "Completed", color: "var(--ok)" },
  cancelled: { label: "Cancelled", color: "var(--danger)" },
};
const STATUS_KEYS: EventStatus[] = ["scheduled", "completed", "cancelled"];

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}
function toYMD(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
/** Parse a "YYYY-MM-DD" date string as a local calendar date (avoids UTC shift). */
function parseYMD(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}
function statusMeta(key: string) {
  return STATUS_META[key] ?? { label: key, color: "var(--muted)" };
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

export function Events() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const today = useMemo(() => new Date(), []);
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [status, setStatus] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() });

  const params = new URLSearchParams({ limit: "200" });
  if (status) params.set("status", status);

  const listQ = useQuery({
    queryKey: ["events", status],
    queryFn: () => api.get<EventPage>(`/events?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const items = listQ.data?.items ?? [];

  // Bucket events by their YYYY-MM-DD so the calendar and list can look them up fast.
  const byDay = useMemo(() => {
    const map = new Map<string, EventOut[]>();
    for (const e of items) {
      const arr = map.get(e.event_date) ?? [];
      arr.push(e);
      map.set(e.event_date, arr);
    }
    for (const arr of map.values()) {
      arr.sort((a, b) => (a.start_time ?? "").localeCompare(b.start_time ?? ""));
    }
    return map;
  }, [items]);

  // 6-week grid starting on the Sunday on/before the 1st (Date handles overflow).
  const cells = useMemo(() => {
    const first = new Date(cursor.year, cursor.month, 1);
    const startOffset = first.getDay();
    return Array.from({ length: 42 }, (_, i) => new Date(cursor.year, cursor.month, 1 - startOffset + i));
  }, [cursor]);

  const todayYMD = toYMD(today);

  const stepMonth = (delta: number) => {
    setCursor((c) => {
      const d = new Date(c.year, c.month + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() };
    });
  };
  const goToday = () => setCursor({ year: today.getFullYear(), month: today.getMonth() });

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Events</h1>
          <p className={styles.subtitle}>Outreach, tabling, and info sessions across the detachment's calendar.</p>
        </div>
        {canWrite && (
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            Add event
          </button>
        )}
      </div>

      <div className={styles.toolbar}>
        <div className={styles.viewToggle} role="tablist" aria-label="Event view">
          <button
            role="tab"
            aria-selected={view === "calendar"}
            className={`${styles.toggleBtn} ${view === "calendar" ? styles.toggleBtnActive : ""}`}
            onClick={() => setView("calendar")}
          >
            Calendar
          </button>
          <button
            role="tab"
            aria-selected={view === "list"}
            className={`${styles.toggleBtn} ${view === "list" ? styles.toggleBtnActive : ""}`}
            onClick={() => setView("list")}
          >
            List
          </button>
        </div>

        <div className={styles.filters}>
          <button
            className={`${styles.filterChip} ${status === null ? styles.filterChipActive : ""}`}
            onClick={() => setStatus(null)}
          >
            All
          </button>
          {STATUS_KEYS.map((s) => (
            <button
              key={s}
              className={`${styles.filterChip} ${status === s ? styles.filterChipActive : ""}`}
              onClick={() => setStatus(status === s ? null : s)}
            >
              <span className={styles.filterDot} style={{ background: statusMeta(s).color }} aria-hidden />
              {statusMeta(s).label}
            </button>
          ))}
        </div>
      </div>

      {view === "calendar" ? (
        <section className={`card ${styles.calCard}`}>
          <div className={styles.calHead}>
            <h2 className={styles.calMonth}>
              {MONTHS[cursor.month]} <span className={styles.calYear}>{cursor.year}</span>
            </h2>
            <div className={styles.calNav}>
              <button className="btn btn-ghost" onClick={goToday}>Today</button>
              <button className={styles.navBtn} onClick={() => stepMonth(-1)} aria-label="Previous month">‹</button>
              <button className={styles.navBtn} onClick={() => stepMonth(1)} aria-label="Next month">›</button>
            </div>
          </div>

          {listQ.isLoading ? (
            <div className={styles.skeleton} style={{ height: 460 }} />
          ) : (
            <div className={styles.calGrid} role="grid">
              {WEEKDAYS.map((w) => (
                <div key={w} className={styles.weekday} role="columnheader">{w}</div>
              ))}
              {cells.map((d) => {
                const ymd = toYMD(d);
                const inMonth = d.getMonth() === cursor.month;
                const isToday = ymd === todayYMD;
                const dayEvents = byDay.get(ymd) ?? [];
                return (
                  <div
                    key={ymd}
                    role="gridcell"
                    className={`${styles.cell} ${inMonth ? "" : styles.cellOut} ${isToday ? styles.cellToday : ""}`}
                  >
                    <div className={styles.cellDate}>
                      <span className={isToday ? styles.todayNum : undefined}>{d.getDate()}</span>
                    </div>
                    <div className={styles.cellEvents}>
                      {dayEvents.slice(0, 3).map((e) => (
                        <button
                          key={e.id}
                          className={styles.eventPill}
                          onClick={() => navigate(`/events/${e.id}`)}
                          title={`${e.title}${e.location ? ` · ${e.location}` : ""}`}
                        >
                          <span className={styles.pillDot} style={{ background: statusMeta(e.status).color }} aria-hidden />
                          <span className={styles.pillText}>{e.title}</span>
                        </button>
                      ))}
                      {dayEvents.length > 3 && (
                        <button
                          className={styles.moreLink}
                          onClick={() => navigate(`/events/${dayEvents[3].id}`)}
                        >
                          +{dayEvents.length - 3} more
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ) : (
        <UpcomingList items={items} loading={listQ.isLoading} filtered={status !== null} onOpen={(id) => navigate(`/events/${id}`)} />
      )}

      {listQ.isError && (
        <div className={styles.empty}>Couldn't load events. Check that the API is running.</div>
      )}

      {creating && <CreateDrawer onClose={() => setCreating(false)} />}
    </div>
  );
}

function UpcomingList({
  items,
  loading,
  filtered,
  onOpen,
}: {
  items: EventOut[];
  loading: boolean;
  filtered: boolean;
  onOpen: (id: number) => void;
}) {
  const todayYMD = toYMD(new Date());
  const { upcoming, past } = useMemo(() => {
    const sorted = [...items].sort((a, b) => a.event_date.localeCompare(b.event_date) || (a.start_time ?? "").localeCompare(b.start_time ?? ""));
    return {
      upcoming: sorted.filter((e) => e.event_date >= todayYMD),
      past: sorted.filter((e) => e.event_date < todayYMD).reverse(),
    };
  }, [items, todayYMD]);

  if (loading) {
    return <div className={`card ${styles.listCard}`}><div className={styles.skeleton} style={{ height: 320, margin: "var(--sp-4)" }} /></div>;
  }
  if (items.length === 0) {
    return (
      <div className={`card ${styles.listCard}`}>
        <div className={styles.empty}>
          {filtered ? "No events match this status." : "No events yet. Add your first event to start the calendar."}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.listWrap}>
      <ListSection title="Upcoming" events={upcoming} onOpen={onOpen} emptyCopy="Nothing scheduled ahead." />
      {past.length > 0 && <ListSection title="Past" events={past} onOpen={onOpen} muted />}
    </div>
  );
}

function ListSection({
  title,
  events,
  onOpen,
  emptyCopy,
  muted,
}: {
  title: string;
  events: EventOut[];
  onOpen: (id: number) => void;
  emptyCopy?: string;
  muted?: boolean;
}) {
  return (
    <section className={`card ${styles.listCard}`}>
      <div className={styles.listHead}>
        <span className="eyebrow">{title}</span>
        <span className={styles.count}>{events.length}</span>
      </div>
      {events.length === 0 ? (
        <div className={styles.empty}>{emptyCopy}</div>
      ) : (
        <ul className={styles.list}>
          {events.map((e) => {
            const d = parseYMD(e.event_date);
            const time = fmtTime(e.start_time);
            return (
              <li key={e.id}>
                <button className={`${styles.listRow} ${muted ? styles.listRowMuted : ""}`} onClick={() => onOpen(e.id)}>
                  <div className={styles.dateChip}>
                    <span className={styles.dateMonth}>{MONTHS[d.getMonth()].slice(0, 3)}</span>
                    <span className={styles.dateDay}>{d.getDate()}</span>
                  </div>
                  <div className={styles.rowMain}>
                    <div className={styles.rowTitle}>{e.title}</div>
                    <div className={styles.rowMeta}>
                      {e.event_type && <span className={styles.rowType}>{e.event_type}</span>}
                      {time && <span>{time}</span>}
                      {e.location && <span>{e.location}</span>}
                    </div>
                  </div>
                  <span className={styles.statusTag} style={{ color: statusMeta(e.status).color }}>
                    <span className={styles.pillDot} style={{ background: statusMeta(e.status).color }} aria-hidden />
                    {statusMeta(e.status).label}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function CreateDrawer({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: "",
    event_type: "outreach",
    event_date: toYMD(new Date()),
    start_time: "",
    end_time: "",
    location: "",
    status: "scheduled" as EventStatus,
    description: "",
  });
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const create = useMutation({
    mutationFn: (body: EventCreate) => api.post<EventOut>("/events", body),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["events"] });
      navigate(`/events/${created.id}`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't create the event."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const body: EventCreate = {
      title: form.title.trim(),
      event_type: form.event_type.trim() || "outreach",
      event_date: form.event_date,
      start_time: form.start_time.trim() || null,
      end_time: form.end_time.trim() || null,
      location: form.location.trim() || null,
      status: form.status,
      description: form.description.trim() || null,
      attendees_count: 0,
    };
    create.mutate(body);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Add event</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.field}>
          <label className="field-label" htmlFor="title">Title</label>
          <input id="title" className="input" value={form.title} onChange={set("title")} required autoFocus />
        </div>

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label className="field-label" htmlFor="event_type">Type</label>
            <input id="event_type" className="input" value={form.event_type} onChange={set("event_type")} placeholder="outreach" />
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

        <div className={styles.field}>
          <label className="field-label" htmlFor="event_date">Date</label>
          <input id="event_date" className="input" type="date" value={form.event_date} onChange={set("event_date")} required />
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

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add event"}
          </button>
        </div>
      </form>
    </div>
  );
}
