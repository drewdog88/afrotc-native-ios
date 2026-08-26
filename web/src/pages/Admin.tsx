/* Admin console — manage who can sign in and audit what they've done. Two panels:
   a Users table (role + active state, add-user drawer, inline role/active edits and
   delete) and a reverse-chronological activity log. The whole screen is gated on the
   signed-in user being an admin; recruiters see a restricted notice instead. */
import { useEffect, useState, type FormEvent } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./Admin.module.css";

type UserOut = components["schemas"]["UserOut"];
type AdminUserCreate = components["schemas"]["AdminUserCreate"];
type AdminUserUpdate = components["schemas"]["AdminUserUpdate"];
type UserPage = components["schemas"]["Page_UserOut_"];
type ActivityLogOut = components["schemas"]["ActivityLogOut"];
type ActivityPage = components["schemas"]["Page_ActivityLogOut_"];
type UserRole = components["schemas"]["UserRole"];
type IntakeSettingsOut = components["schemas"]["IntakeSettingsOut"];
type IntakeSettingsUpdate = components["schemas"]["IntakeSettingsUpdate"];

const ROLES: UserRole[] = ["admin", "recruiter", "viewer"];
const ACTIVITY_PAGE = 25;

function roleLabel(role: string): string {
  if (role === "admin") return "Admin";
  if (role === "recruiter") return "Recruiter";
  if (role === "viewer") return "Viewer (read-only)";
  return role;
}

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

export function Admin() {
  const { user } = useAuth();

  if (!user?.is_admin) {
    return (
      <div className={styles.page}>
        <div className={styles.head}>
          <div>
            <h1 className={styles.title}>Admin</h1>
            <p className={styles.subtitle}>Manage accounts and review activity.</p>
          </div>
        </div>
        <section className={`card ${styles.restricted}`}>
          <span className={styles.restrictedMark} aria-hidden>🔒</span>
          <h2 className={styles.restrictedTitle}>Admins only</h2>
          <p className={styles.restrictedBody}>
            This area is limited to detachment administrators. Ask an admin if you need access to manage
            accounts or review the activity log.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Admin</h1>
          <p className={styles.subtitle}>Manage who can sign in and review what the team has done.</p>
        </div>
      </div>

      <UsersPanel currentUserId={user.id} />
      <ActivityPanel />
      <IntakeSettingsPanel />
    </div>
  );
}

/* ---------------------------------------------------------------- Users ---- */

function UsersPanel({ currentUserId }: { currentUserId: number }) {
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);

  const params = new URLSearchParams({ limit: "200" });
  if (search.trim()) params.set("search", search.trim());

  const usersQ = useQuery({
    queryKey: ["admin-users", search.trim()],
    queryFn: () => api.get<UserPage>(`/admin/users?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const users = usersQ.data?.items ?? [];

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <div>
          <h2 className={styles.sectionTitle}>Users</h2>
          <span className={styles.sectionNote}>Accounts that can sign in to Det 695 tools</span>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          Add user
        </button>
      </div>

      <div className={styles.toolbar}>
        <input
          className={`input ${styles.search}`}
          placeholder="Search by name, username, or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search users"
        />
      </div>

      <div className={`card ${styles.tableWrap}`}>
        {usersQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 260, margin: "var(--sp-4)" }} />
        ) : usersQ.isError ? (
          <div className={styles.empty}>Couldn't load users. Check that the API is running.</div>
        ) : users.length === 0 ? (
          <div className={styles.empty}>{search ? "No users match this search." : "No users yet."}</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th className={styles.colHide}>Username</th>
                <th className={styles.colHide}>Email</th>
                <th>Role</th>
                <th>State</th>
                <th className={styles.right}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <UserRow key={u.id} user={u} isSelf={u.id === currentUserId} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {creating && <CreateUserDrawer onClose={() => setCreating(false)} />}
    </section>
  );
}

function UserRow({ user, isSelf }: { user: UserOut; isSelf: boolean }) {
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-users"] });
    qc.invalidateQueries({ queryKey: ["admin-activity"] });
  };

  const update = useMutation({
    mutationFn: (body: AdminUserUpdate) => api.patch<UserOut>(`/admin/users/${user.id}`, body),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't update this user."),
  });

  const remove = useMutation({
    mutationFn: () => api.del(`/admin/users/${user.id}`),
    onSuccess: () => {
      setConfirmDelete(false);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't remove this user."),
  });

  const busy = update.isPending || remove.isPending;

  return (
    <tr className={styles.row}>
      <td>
        <div className={styles.name}>{user.full_name}</div>
        {isSelf && <div className={styles.sub}>You</div>}
        {error && <div className={styles.rowError}>{error}</div>}
      </td>
      <td className={styles.colHide}>
        <span className="mono">{user.username}</span>
      </td>
      <td className={styles.colHide}>{user.email || <span className={styles.muted}>—</span>}</td>
      <td>
        <select
          className={styles.rolePicker}
          value={user.role}
          disabled={busy}
          aria-label={`Role for ${user.full_name}`}
          onChange={(e) => {
            setError(null);
            update.mutate({ role: e.target.value as UserRole });
          }}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {roleLabel(r)}
            </option>
          ))}
        </select>
      </td>
      <td>
        <button
          type="button"
          className={`${styles.stateChip} ${user.is_active ? styles.stateActive : styles.stateInactive}`}
          disabled={busy || isSelf}
          title={isSelf ? "You can't change your own active state" : user.is_active ? "Deactivate this account" : "Reactivate this account"}
          onClick={() => {
            setError(null);
            update.mutate({ is_active: !user.is_active });
          }}
        >
          <span className={styles.stateDot} aria-hidden />
          {user.is_active ? "Active" : "Inactive"}
        </button>
        <button
          type="button"
          className={`${styles.stateChip} ${user.two_factor_enabled ? styles.stateActive : styles.stateInactive}`}
          disabled={busy}
          title={user.two_factor_enabled ? "Turn off email 2FA for this account" : "Turn on email 2FA for this account"}
          onClick={() => {
            setError(null);
            update.mutate({ two_factor_enabled: !user.two_factor_enabled });
          }}
        >
          <span className={styles.stateDot} aria-hidden />
          {user.two_factor_enabled ? "2FA on" : "2FA off"}
        </button>
        {user.is_locked && (
          <span className={styles.sub} title="Locked out of sign-in after too many failed attempts">
            🔒 Locked
          </span>
        )}
      </td>
      <td className={styles.right}>
        <div className={styles.confirmRow}>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={busy}
            onClick={() => {
              setError(null);
              setEditing(true);
            }}
          >
            Edit
          </button>
          {confirmDelete ? (
            <>
              <span className={styles.confirmText}>Remove?</span>
              <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => setConfirmDelete(false)}>
                Cancel
              </button>
              <button type="button" className={styles.dangerBtn} disabled={busy} onClick={() => remove.mutate()}>
                {remove.isPending ? "Removing…" : "Remove"}
              </button>
            </>
          ) : (
            <button
              type="button"
              className="btn btn-ghost"
              disabled={busy || isSelf}
              title={isSelf ? "You can't remove your own account" : "Remove this user"}
              onClick={() => {
                setError(null);
                setConfirmDelete(true);
              }}
            >
              Remove
            </button>
          )}
        </div>
        {editing && <EditUserDrawer user={user} onClose={() => setEditing(false)} />}
      </td>
    </tr>
  );
}

function CreateUserDrawer({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    phone: "",
    password: "",
    role: "recruiter" as UserRole,
    secret_question: "",
    secret_answer: "",
  });
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const create = useMutation({
    mutationFn: (body: AdminUserCreate) => api.post<UserOut>("/admin/users", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-activity"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't create the user."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const body: AdminUserCreate = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      username: form.username.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      password: form.password,
      role: form.role,
      secret_question: form.secret_question.trim(),
      secret_answer: form.secret_answer.trim(),
    };
    create.mutate(body);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Add user</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
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
          <label className="field-label" htmlFor="username">Username</label>
          <input id="username" className="input" value={form.username} onChange={set("username")} required />
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
            <label className="field-label" htmlFor="password">Temporary password</label>
            <input id="password" className="input" type="password" value={form.password} onChange={set("password")} required />
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="role">Role</label>
            <select id="role" className={styles.select} value={form.role} onChange={set("role")}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {roleLabel(r)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="secret_question">Security question</label>
          <input id="secret_question" className="input" value={form.secret_question} onChange={set("secret_question")} required />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="secret_answer">Security answer</label>
          <input id="secret_answer" className="input" value={form.secret_answer} onChange={set("secret_answer")} required />
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add user"}
          </button>
        </div>
      </form>
    </div>
  );
}

function EditUserDrawer({ user, onClose }: { user: UserOut; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    phone: user.phone ?? "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-users"] });
    qc.invalidateQueries({ queryKey: ["admin-activity"] });
  };

  const save = useMutation({
    mutationFn: (body: AdminUserUpdate) => api.patch<UserOut>(`/admin/users/${user.id}`, body),
    onSuccess: () => {
      invalidate();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save these changes."),
  });

  const unlock = useMutation({
    mutationFn: () =>
      api.patch<UserOut>(`/admin/users/${user.id}`, { is_locked: false, failed_login_attempts: 0 }),
    onSuccess: () => {
      invalidate();
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't unlock this account."),
  });

  const revokeDevices = useMutation({
    mutationFn: () => api.adminRevokeTrustedDevices(user.id),
    onSuccess: (res) => {
      setError(null);
      setNotice(res.detail || "Trusted devices revoked.");
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't revoke trusted devices."),
  });

  const busy = save.isPending || unlock.isPending || revokeDevices.isPending;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const body: AdminUserUpdate = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
    };
    if (form.password) body.password = form.password;
    save.mutate(body);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Edit {user.full_name}</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}
        {notice && !error && <div className={styles.sub}>{notice}</div>}

        {user.is_locked && (
          <div className={styles.formError}>
            This account is locked out of sign-in.{" "}
            <button
              type="button"
              className="btn btn-ghost"
              disabled={busy}
              onClick={() => {
                setError(null);
                unlock.mutate();
              }}
            >
              {unlock.isPending ? "Unlocking…" : "Unlock account"}
            </button>
          </div>
        )}

        <div className={styles.field}>
          <span className="field-label">Trusted devices</span>
          <div>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={busy}
              onClick={() => {
                setError(null);
                setNotice(null);
                revokeDevices.mutate();
              }}
            >
              {revokeDevices.isPending ? "Revoking…" : "Revoke trusted devices"}
            </button>
          </div>
          <span className={styles.sectionNote}>
            Signs this account out of every device it previously chose to trust for email 2FA.
          </span>
        </div>

        <div className={styles.formRow}>
          <div className={styles.field}>
            <label className="field-label" htmlFor="edit_first_name">First name</label>
            <input id="edit_first_name" className="input" value={form.first_name} onChange={set("first_name")} required autoFocus />
          </div>
          <div className={styles.field}>
            <label className="field-label" htmlFor="edit_last_name">Last name</label>
            <input id="edit_last_name" className="input" value={form.last_name} onChange={set("last_name")} required />
          </div>
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="edit_email">Email</label>
          <input id="edit_email" className="input" type="email" value={form.email} onChange={set("email")} required />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="edit_phone">Phone</label>
          <input id="edit_phone" className="input" value={form.phone} onChange={set("phone")} />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="edit_password">Reset password</label>
          <input
            id="edit_password"
            className="input"
            type="password"
            value={form.password}
            onChange={set("password")}
            placeholder="Leave blank to keep current password"
            autoComplete="new-password"
          />
          <span className={styles.sectionNote}>
            If set, the user must choose a new password at their next sign-in.
          </span>
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {save.isPending ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------- Activity ---- */

function ActivityPanel() {
  const [limit, setLimit] = useState(ACTIVITY_PAGE);

  const activityQ = useQuery({
    queryKey: ["admin-activity", limit],
    queryFn: () => api.get<ActivityPage>(`/admin/activity?skip=0&limit=${limit}`),
    placeholderData: keepPreviousData,
  });

  const items = activityQ.data?.items ?? [];
  const total = activityQ.data?.total ?? 0;
  const sorted = [...items].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  const hasMore = items.length < total;

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <div>
          <h2 className={styles.sectionTitle}>Activity log</h2>
          <span className={styles.sectionNote}>Newest first · what the team has changed</span>
        </div>
      </div>

      <div className={`card ${styles.tableWrap}`}>
        {activityQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 260, margin: "var(--sp-4)" }} />
        ) : activityQ.isError ? (
          <div className={styles.empty}>Couldn't load the activity log.</div>
        ) : sorted.length === 0 ? (
          <div className={styles.empty}>No activity recorded yet.</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Action</th>
                <th className={styles.colHide}>Record</th>
                <th>Who</th>
                <th className={styles.right}>When</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((ev: ActivityLogOut) => (
                <tr key={ev.id} className={styles.rowStatic}>
                  <td>
                    <div className={styles.name}>{ev.action}</div>
                    {ev.details && <div className={styles.sub}>{ev.details}</div>}
                  </td>
                  <td className={styles.colHide}>
                    {ev.record_description || ev.table_name ? (
                      <span className={styles.recordCell}>
                        {ev.record_description || ev.table_name}
                        {ev.table_name && ev.record_id != null && (
                          <span className={styles.muted}> · #{ev.record_id}</span>
                        )}
                      </span>
                    ) : (
                      <span className={styles.muted}>—</span>
                    )}
                  </td>
                  <td>
                    <span className="mono">{ev.username}</span>
                  </td>
                  <td className={`${styles.right} ${styles.muted}`}>{fmtDate(ev.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {!activityQ.isLoading && !activityQ.isError && sorted.length > 0 && (
        <div className={styles.activityFoot}>
          <span className={styles.count}>
            Showing {sorted.length} of {total}
          </span>
          {hasMore && (
            <button
              type="button"
              className="btn btn-ghost"
              disabled={activityQ.isFetching}
              onClick={() => setLimit((n) => n + ACTIVITY_PAGE)}
            >
              {activityQ.isFetching ? "Loading…" : "Load more"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------ Intake settings ---- */

function IntakeSettingsPanel() {
  const qc = useQueryClient();
  const [seeded, setSeeded] = useState(false);
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const settingsQ = useQuery({
    queryKey: ["intake-settings"],
    queryFn: api.getIntakeSettings,
  });

  useEffect(() => {
    if (settingsQ.data && !seeded) {
      const data: IntakeSettingsOut = settingsQ.data;
      setEmail(data.recruiter_notification_email ?? "");
      setSubject(data.ack_email_subject);
      setBody(data.ack_email_body);
      setSeeded(true);
    }
  }, [settingsQ.data, seeded]);

  const save = useMutation({
    mutationFn: (payload: IntakeSettingsUpdate) => api.updateIntakeSettings(payload),
    onSuccess: () => {
      setSaved(true);
      qc.invalidateQueries({ queryKey: ["intake-settings"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save these settings."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    save.mutate({
      recruiter_notification_email: email.trim() || null,
      ack_email_subject: subject.trim(),
      ack_email_body: body,
    });
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <div>
          <h2 className={styles.sectionTitle}>Request-Info Settings</h2>
          <span className={styles.sectionNote}>
            Recruiter notification email and the applicant acknowledgment template
          </span>
        </div>
      </div>

      <div className="card" style={{ padding: "var(--sp-4)" }}>
        {settingsQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 260 }} />
        ) : settingsQ.isError ? (
          <div className={styles.empty}>Couldn't load Request-Info settings. Check that the API is running.</div>
        ) : (
          <form className={styles.section} onSubmit={onSubmit}>
            {error && <div className={styles.formError}>{error}</div>}
            {saved && !error && <div className={styles.sub}>Saved.</div>}

            <div className={styles.field}>
              <label className="field-label" htmlFor="recruiter_notification_email">
                Recruiter notification email
              </label>
              <input
                id="recruiter_notification_email"
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="recruiter@det695.org"
              />
            </div>

            <div className={styles.field}>
              <label className="field-label" htmlFor="ack_email_subject">
                Acknowledgment email subject
              </label>
              <input
                id="ack_email_subject"
                className="input"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>

            <div className={styles.field}>
              <label className="field-label" htmlFor="ack_email_body">
                Acknowledgment email body
              </label>
              <textarea
                id="ack_email_body"
                className={`input ${styles.templateArea}`}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
              />
              <span className={styles.sectionNote}>
                Use <code>{"{{first_name}}"}</code> to personalize. Links are clickable in the email.
              </span>
            </div>

            <div>
              <button type="submit" className="btn btn-primary" disabled={save.isPending}>
                {save.isPending ? "Saving…" : "Save settings"}
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
