/* Temporary stand-in for screens not yet built, so the nav never dead-ends during
   the prototype phase. Each names what will live here. */
import { useLocation } from "react-router-dom";

const COPY: Record<string, { title: string; text: string }> = {
  "/recruits": { title: "Recruits", text: "Prospect list with stage control and stage history." },
  "/pipeline": { title: "Pipeline", text: "Kanban-style board to advance recruits through the ascent." },
  "/follow-ups": { title: "Follow-ups", text: "Assignable tasks and reminders so prospects don't go cold." },
  "/cadets": { title: "Cadets", text: "Enrolled cadet roster with status and unenrollment tracking." },
  "/contacts": { title: "Contacts", text: "High-school and university points of contact." },
  "/events": { title: "Events", text: "Recruiting events with a calendar view." },
  "/map": { title: "Territory", text: "Map of schools, contacts, and events across the recruiting area." },
  "/import": { title: "Bulk import", text: "Upload a CSV or Excel prospect list, preview, validate, and commit." },
  "/materials": { title: "Materials", text: "Shared recruiting documents and links." },
  "/profile": { title: "Profile", text: "Your account, password, and two-factor settings." },
};

export function Placeholder() {
  const { pathname } = useLocation();
  const key = Object.keys(COPY).find((k) => pathname.startsWith(k));
  const c = key ? COPY[key] : { title: "Coming soon", text: "This screen is on the way." };
  return (
    <div style={{ maxWidth: 560 }}>
      <div className="eyebrow" style={{ marginBottom: 8 }}>Next up</div>
      <h1 style={{ fontSize: "var(--t-2xl)", marginBottom: 8 }}>{c.title}</h1>
      <p style={{ color: "var(--muted)" }}>{c.text}</p>
    </div>
  );
}
