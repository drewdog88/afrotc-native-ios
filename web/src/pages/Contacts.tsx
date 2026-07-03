/* Recruiting contacts — the people at high schools and universities the detachment
   works through to reach prospects. Search + scope the roster by active status, open a
   contact to view/edit their details, or add a new point of contact. Two routes live
   here: the list (/contacts) and the detail/edit view (/contacts/:id). */
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import type { components } from "../api/schema";
import styles from "./Contacts.module.css";

type ContactOut = components["schemas"]["ContactOut"];
type ContactCreate = components["schemas"]["ContactCreate"];
type ContactUpdate = components["schemas"]["ContactUpdate"];
type ContactPage = components["schemas"]["Page_ContactOut_"];

type ActiveFilter = "all" | "active" | "inactive";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return (
    d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) +
    " · " +
    d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
  );
}

function StatusChip({ active, size }: { active: boolean; size?: "sm" }) {
  return (
    <span
      className={`${styles.statusChip} ${active ? styles.statusActive : styles.statusInactive} ${
        size === "sm" ? styles.statusSm : ""
      }`}
    >
      <span className={styles.statusDot} aria-hidden />
      {active ? "Active" : "Inactive"}
    </span>
  );
}

// ---- List ----------------------------------------------------------------

export function Contacts() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<ActiveFilter>("all");
  const [creating, setCreating] = useState(false);

  const params = new URLSearchParams({ limit: "200" });
  if (search.trim()) params.set("search", search.trim());
  if (filter === "active") params.set("is_active", "true");
  if (filter === "inactive") params.set("is_active", "false");

  const listQ = useQuery({
    queryKey: ["contacts", search.trim(), filter],
    queryFn: () => api.get<ContactPage>(`/contacts?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const items = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;

  const filters: { key: ActiveFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "active", label: "Active" },
    { key: "inactive", label: "Inactive" },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Contacts</h1>
          <p className={styles.subtitle}>
            The high school and university points of contact the detachment recruits through.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          Add contact
        </button>
      </div>

      <div className={styles.toolbar}>
        <input
          className={`input ${styles.search}`}
          placeholder="Search by name, school, or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search contacts"
        />
        <div className={styles.filters} role="group" aria-label="Filter by status">
          {filters.map((f) => (
            <button
              key={f.key}
              className={`${styles.filterChip} ${filter === f.key ? styles.filterChipActive : ""}`}
              onClick={() => setFilter(f.key)}
              aria-pressed={filter === f.key}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <section className={`card ${styles.tableWrap}`}>
        {listQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 320, margin: "var(--sp-4)" }} />
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            {search || filter !== "all"
              ? "No contacts match this view."
              : "No contacts yet. Add your first point of contact to get started."}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th className={styles.colHide}>School</th>
                <th className={styles.colHide}>Email</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className={styles.row} onClick={() => navigate(`/contacts/${c.id}`)}>
                  <td>
                    <div className={styles.name}>{c.contact_name}</div>
                    {c.contact_title && <div className={styles.sub}>{c.contact_title}</div>}
                  </td>
                  <td className={styles.colHide}>
                    {c.university_name || <span className={styles.muted}>—</span>}
                  </td>
                  <td className={styles.colHide}>
                    {c.email || <span className={styles.muted}>—</span>}
                  </td>
                  <td>
                    <StatusChip active={c.is_active} size="sm" />
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
          {total > items.length ? ` of ${total}` : ""} contact{total === 1 ? "" : "s"}
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
    contact_name: "",
    contact_title: "",
    university_name: "",
    email: "",
    phone: "",
    address: "",
    notes: "",
    is_active: true,
  });
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const create = useMutation({
    mutationFn: (body: ContactCreate) => api.post<ContactOut>("/contacts", body),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      navigate(`/contacts/${created.id}`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't create the contact."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const body: ContactCreate = {
      contact_name: form.contact_name.trim(),
      contact_title: form.contact_title.trim() || null,
      university_name: form.university_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      notes: form.notes.trim() || null,
      is_active: form.is_active,
    };
    create.mutate(body);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Add contact</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.field}>
          <label className="field-label" htmlFor="contact_name">Contact name</label>
          <input id="contact_name" className="input" value={form.contact_name} onChange={set("contact_name")} required autoFocus />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="contact_title">Title or role</label>
          <input id="contact_title" className="input" value={form.contact_title} onChange={set("contact_title")} placeholder="e.g. Guidance counselor" />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="university_name">School or university</label>
          <input id="university_name" className="input" value={form.university_name} onChange={set("university_name")} required />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="email">Email</label>
          <input id="email" className="input" type="email" value={form.email} onChange={set("email")} required />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="phone">Phone</label>
          <input id="phone" className="input" value={form.phone} onChange={set("phone")} />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="address">Address</label>
          <textarea id="address" className={styles.noteInput} value={form.address} onChange={set("address")} />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="notes">Notes</label>
          <textarea id="notes" className={styles.noteInput} value={form.notes} onChange={set("notes")} />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="is_active">Status</label>
          <select
            id="is_active"
            className={styles.select}
            value={form.is_active ? "active" : "inactive"}
            onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.value === "active" }))}
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add contact"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---- Detail --------------------------------------------------------------

export function ContactDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const contactQ = useQuery({
    queryKey: ["contact", id],
    queryFn: () => api.get<ContactOut>(`/contacts/${id}`),
    enabled: !!id,
  });

  const contact = contactQ.data;

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["contact", id] });
    qc.invalidateQueries({ queryKey: ["contacts"] });
  };

  const remove = useMutation({
    mutationFn: () => api.del(`/contacts/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      navigate("/contacts");
    },
  });

  if (contactQ.isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.skeleton} style={{ height: 48, width: 280 }} />
        <div className={styles.skeleton} style={{ height: 360 }} />
      </div>
    );
  }

  if (contactQ.isError || !contact) {
    return (
      <div className={styles.page}>
        <button className={styles.back} onClick={() => navigate("/contacts")}>← Back to contacts</button>
        <div className={styles.formError}>Couldn't load this contact. They may have been removed.</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <button className={styles.back} onClick={() => navigate("/contacts")}>← Back to contacts</button>

      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>{contact.contact_name}</h1>
          <div className={styles.headMeta}>
            <StatusChip active={contact.is_active} />
            {contact.university_name && <span className={styles.empty}>{contact.university_name}</span>}
          </div>
        </div>
      </div>

      <ProfilePanel
        contact={contact}
        onSaved={invalidateAll}
        onDelete={() => {
          if (window.confirm("Remove this contact? This can't be undone.")) remove.mutate();
        }}
        deleting={remove.isPending}
        deleteError={remove.isError ? (remove.error instanceof ApiError ? remove.error.message : "Couldn't remove the contact.") : null}
      />
    </div>
  );
}

function ProfilePanel({
  contact,
  onSaved,
  onDelete,
  deleting,
  deleteError,
}: {
  contact: ContactOut;
  onSaved: () => void;
  onDelete: () => void;
  deleting: boolean;
  deleteError: string | null;
}) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    contact_name: contact.contact_name,
    contact_title: contact.contact_title ?? "",
    university_name: contact.university_name,
    email: contact.email,
    phone: contact.phone ?? "",
    address: contact.address ?? "",
    notes: contact.notes ?? "",
    is_active: contact.is_active,
  });

  // Keep the form in sync if the contact refetches while not editing.
  useEffect(() => {
    if (!editing) {
      setForm({
        contact_name: contact.contact_name,
        contact_title: contact.contact_title ?? "",
        university_name: contact.university_name,
        email: contact.email,
        phone: contact.phone ?? "",
        address: contact.address ?? "",
        notes: contact.notes ?? "",
        is_active: contact.is_active,
      });
    }
  }, [contact, editing]);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: (body: ContactUpdate) => api.patch<ContactOut>(`/contacts/${contact.id}`, body),
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
      contact_name: form.contact_name.trim(),
      contact_title: form.contact_title.trim() || null,
      university_name: form.university_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      notes: form.notes.trim() || null,
      is_active: form.is_active,
    });
  }

  if (!editing) {
    return (
      <section className={`card ${styles.panel}`}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Contact details</h2>
          <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>
        </div>
        <div className={styles.fields}>
          <Field label="Title / role" value={contact.contact_title} />
          <Field label="School" value={contact.university_name} />
          <LinkField label="Email" value={contact.email} href={contact.email ? `mailto:${contact.email}` : undefined} />
          <LinkField label="Phone" value={contact.phone} href={contact.phone ? `tel:${contact.phone.replace(/\D/g, "")}` : undefined} />
          <div className={styles.fieldFull}>
            <div className={styles.fieldLabel}>Address</div>
            <div className={styles.fieldValue}>{contact.address || <span className={styles.empty}>—</span>}</div>
          </div>
          {contact.latitude != null && contact.longitude != null && (
            <LinkField
              label="Map"
              value="Open in Google Maps"
              href={`https://www.google.com/maps?q=${contact.latitude},${contact.longitude}`}
            />
          )}
          <Field label="Latitude" value={contact.latitude != null ? String(contact.latitude) : null} mono />
          <Field label="Longitude" value={contact.longitude != null ? String(contact.longitude) : null} mono />
          <div className={styles.fieldFull}>
            <div className={styles.fieldLabel}>Notes</div>
            <div className={styles.fieldValue}>{contact.notes || <span className={styles.empty}>—</span>}</div>
          </div>
          <Field label="Added" value={fmtDate(contact.created_at)} mono />
          <Field label="Updated" value={fmtDate(contact.last_modified)} mono />
        </div>

        {deleteError && <div className={styles.formError}>{deleteError}</div>}
        <div className={styles.dangerRow}>
          <button className="btn btn-ghost" onClick={onDelete} disabled={deleting}>
            {deleting ? "Removing…" : "Remove contact"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <form className={`card ${styles.panel}`} onSubmit={onSubmit}>
      <div className={styles.panelHead}>
        <h2 className={styles.panelTitle}>Edit contact</h2>
      </div>
      {error && <div className={styles.formError}>{error}</div>}
      <div className={styles.fields}>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_contact_name">Contact name</label>
          <input id="e_contact_name" className="input" value={form.contact_name} onChange={set("contact_name")} required />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_contact_title">Title or role</label>
          <input id="e_contact_title" className="input" value={form.contact_title} onChange={set("contact_title")} />
        </div>
        <div className={styles.field}>
          <label className="field-label" htmlFor="e_university_name">School or university</label>
          <input id="e_university_name" className="input" value={form.university_name} onChange={set("university_name")} required />
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
          <label className="field-label" htmlFor="e_is_active">Status</label>
          <select
            id="e_is_active"
            className={styles.select}
            value={form.is_active ? "active" : "inactive"}
            onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.value === "active" }))}
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label className="field-label" htmlFor="e_address">Address</label>
          <textarea id="e_address" className={styles.noteInput} value={form.address} onChange={set("address")} />
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label className="field-label" htmlFor="e_notes">Notes</label>
          <textarea id="e_notes" className={styles.noteInput} value={form.notes} onChange={set("notes")} />
        </div>
      </div>
      <div className={styles.editActions}>
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
      <div className={`${styles.fieldValue} ${mono ? "mono" : ""}`}>
        {value || <span className={styles.empty}>—</span>}
      </div>
    </div>
  );
}

function LinkField({ label, value, href }: { label: string; value: string | null | undefined; href?: string }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldLabel}>{label}</div>
      <div className={styles.fieldValue}>
        {href && value ? (
          <a
            href={href}
            onClick={(e) => e.stopPropagation()}
            style={{ cursor: "pointer", color: "var(--link-color, #0070f3)", textDecoration: "underline" }}
          >
            {value}
          </a>
        ) : (
          value || <span className={styles.empty}>—</span>
        )}
      </div>
    </div>
  );
}
