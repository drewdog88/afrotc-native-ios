/* Persistent app frame: navy left rail with grouped navigation + a sticky top bar
   showing the current section and the signed-in user. Renders the routed page via
   <Outlet />. Nav is flat (single shared dashboard for everyone, per the plan). */
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Insignia } from "./Insignia";
import styles from "./AppShell.module.css";

interface NavItem {
  to: string;
  label: string;
  icon: string; // single SVG path
}

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Operations",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: "M3 13h8V3H3v10Zm0 8h8v-6H3v6Zm10 0h8V11h-8v10Zm0-18v6h8V3h-8Z" },
      { to: "/recruits", label: "Recruits", icon: "M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm-8 0a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-2.7 0-8 1.3-8 4v3h9v-3c0-1 .4-1.9 1.1-2.6C9.3 13.1 8.6 13 8 13Zm8 0c-.3 0-.7 0-1.1.1 1.3 1 2.1 2.3 2.1 3.9v3h7v-3c0-2.7-5.3-4-8-4Z" },
      { to: "/pipeline", label: "Pipeline", icon: "M3 3v18h18v-2H5V3H3Zm4 12 4-4 3 3 5-5-1.4-1.4L14 11l-3-3-5 5Z" },
      { to: "/follow-ups", label: "Follow-ups", icon: "M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2Zm6-6V11c0-3.1-1.6-5.6-4.5-6.3V4a1.5 1.5 0 0 0-3 0v.7C7.6 5.4 6 7.9 6 11v5l-2 2v1h16v-1l-2-2Z" },
    ],
  },
  {
    group: "Directory",
    items: [
      { to: "/cadets", label: "Cadets", icon: "M12 2 3 6v6c0 5 3.8 9.4 9 10 5.2-.6 9-5 9-10V6l-9-4Zm0 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm0 14c-2.3 0-4.3-1.2-5.5-3 .1-1.8 3.7-2.8 5.5-2.8s5.4 1 5.5 2.8A6.5 6.5 0 0 1 12 20Z" },
      { to: "/contacts", label: "Contacts", icon: "M20 2H8a2 2 0 0 0-2 2v3H4v2h2v2H4v2h2v2H4v2h2v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2Zm-6 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm5 12h-10c0-2.7 3.3-4 5-4s5 1.3 5 4Z" },
      { to: "/events", label: "Events", icon: "M19 4h-1V2h-2v2H8V2H6v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm0 16H5V10h14v10ZM5 8V6h14v2H5Z" },
      { to: "/map", label: "Territory", icon: "M20 4l-6 2-8-2-4 1.5v14L6 18l8 2 6-2V4Zm-9 2.7 2 .5v10.1l-2-.5V6.7Z" },
    ],
  },
  {
    group: "Resources",
    items: [
      { to: "/import", label: "Bulk import", icon: "M19 9h-4V3H9v6H5l7 7 7-7ZM5 18v2h14v-2H5Z" },
      { to: "/materials", label: "Materials", icon: "M4 4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2H4Z" },
    ],
  },
];

const ALL_ITEMS = NAV.flatMap((g) => g.items);

function initials(user: { username: string; full_name?: string | null }): string {
  const name = user.full_name?.trim() || user.username;
  const parts = name.split(/\s+/);
  return (parts[0]?.[0] ?? "").concat(parts[1]?.[0] ?? "").toUpperCase() || name.slice(0, 2).toUpperCase();
}

export function AppShell() {
  const { user, logout, canWrite } = useAuth();
  const location = useLocation();
  const current = ALL_ITEMS.find((i) => location.pathname.startsWith(i.to));

  // Bulk import is a write-only flow — hide it from read-only viewers.
  const nav = NAV.map((group) => ({
    ...group,
    items: group.items.filter((i) => canWrite || i.to !== "/import"),
  })).filter((group) => group.items.length > 0);

  return (
    <div className={styles.shell}>
      <aside className={styles.rail}>
        <div className={styles.brand}>
          <Insignia />
          <div className={styles.brandText}>
            <span className={styles.brandName}>Det 695</span>
            <span className={styles.brandSub}>Recruiting Ops</span>
          </div>
        </div>

        <nav className={styles.nav}>
          {nav.map((group) => (
            <div key={group.group}>
              <div className={styles.navGroup}>{group.group}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
                >
                  <svg className={styles.icon} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d={item.icon} />
                  </svg>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className={styles.railFoot}>
          <NavLink
            to="/profile"
            className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
          >
            <svg className={styles.icon} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm0 2c-3.3 0-10 1.7-10 5v3h20v-3c0-3.3-6.7-5-10-5Z" />
            </svg>
            Profile
          </NavLink>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div className={styles.crumb}>{current?.label ?? "Det 695"}</div>
          <div className={styles.barActions}>
            <button className={styles.iconBtn} onClick={() => void logout()} title="Sign out" aria-label="Sign out">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M16 13v-2H7V8l-5 4 5 4v-3h9ZM20 3h-9v2h9v14h-9v2h9a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Z" />
              </svg>
            </button>
            {user && (
              <div className={styles.user}>
                <div className={styles.avatar}>{initials(user)}</div>
                <span>{user.full_name || user.username}</span>
              </div>
            )}
          </div>
        </header>
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
