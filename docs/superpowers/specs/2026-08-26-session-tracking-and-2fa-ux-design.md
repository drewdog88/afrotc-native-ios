# Session Tracking + 2FA UX Design

**Status:** approved (design) · **Date:** 2026-08-26 · **Branch:** `session-tracking-and-2fa-ux`

## Goal

Give the signed-in user a real view of the devices logged into their account and the ability to sign any of them out remotely — motivated by the PII this app holds — and fix three 2FA UX problems on the way: the blocking first-login enrollment popup, the missing on/off toggle, and the off-theme code-entry box.

## Context / what exists today (verified in code)

- **Login 2FA is already a hard gate.** `POST /auth/login` returns only a `challenge_token` (no access/refresh) when 2FA is active; the web app routes to a dedicated `/login/verify` screen and `RequireAuth` blocks all app content until a real token pair exists (`user` stays `null`). No PII renders behind the login code box. The see-through overlay the user saw is the **post-login enrollment nudge** (`EnrollmentPrompt`), which only shows once already authenticated.
- **Tokens are stateless JWTs.** Access (`type=access`), refresh (`type=refresh`), challenge (`type=login_2fa`). `get_current_user` accepts only `type=access`. No server-side token/session store.
- **Logins are audited** only as generic `ActivityLog` rows (`action="LOGIN"`, with IP + user-agent + timestamp) via `_record_login`. There is **no session lifecycle, no logout event, and no way to revoke** an issued token.
- **`logout` is a no-op** (204, stateless). A leaked refresh token is valid until natural expiry.
- Trusted-device trust persists across logout by design (the "trust this device for 30 days" feature). We keep that behavior.

## Non-goals (explicit)

- Moving tokens out of `localStorage` (XSS surface) — noted, out of scope here.
- TOTP (scaffolding stays dormant).
- IP geolocation, failed-login audit rows, "new device" email alerts.
- Merging trusted-devices and sessions into one list — they are different concepts and stay separate, clearly labeled.

## Architecture

### Backend — a server-side session store keyed by a `sid` claim

**New model `AuthSession` → table `auth_sessions`** (`backend/app/models/auth_session.py`, exported from `models/__init__.py`):

| column | type | notes |
|---|---|---|
| `id` | int pk | |
| `user_id` | int FK `users.id`, indexed, not null | |
| `sid` | str(36), unique, indexed, not null | session id (uuid4); embedded as `sid` claim in access + refresh JWTs |
| `device_label` | str(255) nullable | derived from user-agent (best-effort parse) |
| `ip_address` | str(45) nullable | from `x-forwarded-for` / client |
| `user_agent` | str(500) nullable | |
| `created_at` | tz-aware datetime, default `now_utc` | |
| `last_seen_at` | tz-aware datetime, default `now_utc` | bumped on every refresh |
| `expires_at` | tz-aware datetime, not null | `created_at + refresh_token_expire_days` — the outer session lifetime |
| `revoked_at` | tz-aware datetime nullable | set on sign-out / logout |

A session is **valid** iff `revoked_at IS NULL AND expires_at > now`.

**Token changes** (`backend/app/core/security.py`): `create_access_token` and `create_refresh_token` gain a `sid` argument, embedded as an `extra` claim. Challenge token unchanged.

**Per-request revocation** (`backend/app/api/deps.py`): `get_current_user` decodes the access token, and — new — loads the `AuthSession` by `sid` and requires it valid; otherwise 401. This makes "sign out this device" take effect on the next request (immediate at this scale). A new dependency `get_current_session(creds, db) -> AuthSession` returns the validated session (used by `get_current_user` and by `logout`). **Access tokens issued before this change carry no `sid` and are rejected — everyone re-logs in once after deploy.** (2 users; acceptable.)

**Auth flow** (`backend/app/api/v1/auth.py`):
- New helper `_start_session(db, user, request) -> AuthSession` creates a session row (new `sid`, device/ip/ua, `expires_at`).
- `_issue_token_pair(user, sid)` now takes the `sid`.
- **Login** (no-2FA path, trusted-device path) and **`/auth/login/verify`**: start a session, issue the pair with its `sid`, keep the existing `ActivityLog` `LOGIN` row.
- **`/auth/refresh`**: decode refresh → load session by `sid` → require valid → bump `last_seen_at` → mint new access with same `sid`. Invalid session → 401.
- **`/auth/logout`**: depend on `get_current_session`, set `revoked_at = now`, return 204. (Client still clears `localStorage` tokens.)

**New endpoints** (add to `backend/app/api/v1/profile.py`; admin one to `admin.py`):
- `GET /profile/sessions` → list the caller's **valid** sessions; each item `{ id, device_label, ip_address, created_at, last_seen_at, expires_at, current: bool }`. `current` computed by comparing the row's `sid` to the caller's token `sid`. **`sid` is never returned to the client.**
- `DELETE /profile/sessions/{id}` → revoke that session; 404 if not the caller's.
- `POST /profile/sessions/revoke-others` → revoke all the caller's valid sessions except the current `sid`.
- `POST /admin/users/{user_id}/revoke-sessions` → admin revokes all of a user's sessions (parallels existing `adminRevokeTrustedDevices`).

**Schemas** (`backend/app/schemas/`): `SessionOut` for the list item above.

**Migration:** new Alembic revision, `down_revision = email2fa0001` (current head), creating only `auth_sessions`. Additive → safe to apply to the direct (non-pooled) Neon host **before** deploying code.

### Web

- **api client** (`web/src/lib/api.ts`): `listSessions()` → `GET /profile/sessions`; `revokeSession(id)` → `DELETE /profile/sessions/{id}`; `revokeOtherSessions()` → `POST /profile/sessions/revoke-others`. (`logout()` unchanged — server now revokes.)
- **Profile** (`web/src/pages/Profile.tsx`): new **`SignedInDevicesCard`**, always visible, lists active sessions (device, IP, last seen, "This device" tag on `current`), a **Sign out** button per row (disabled on the current row), and **Sign out all other devices** when >1. Uses the existing CSS-module theme classes.
- **2FA toggle**: replace the Enable/Turn-off buttons in `TwoFactorCard` with a themed on/off **switch** (`styles.switch` in `Profile.module.css`). Flipping **on** starts email enrollment → inline themed code entry (the existing `awaitingCode` step, restyled); flipping **off** disables (keeps the "trusted devices signed out" note).
- **Enrollment nudge → non-blocking banner**: delete the `EnrollmentPrompt` modal; add **`EnrollmentBanner`** rendered in `AppShell` above content — a thin dismissible strip: "Add an email code at sign-in for extra security · **Turn on** / **Not now**". **Turn on** routes to `/profile`; **Not now** calls `twoFAEnrollmentDismiss()`. No gray-out, no trap, no code entry in the banner.
- **Code box theme**: a shared `styles.codeInput` used by both the Profile enrollment step and `LoginVerify`; consistent app colors/fonts, centered mono digits.

## Data flow (sign out a device)

1. User opens Profile → `GET /profile/sessions` lists valid sessions, current one tagged.
2. User clicks **Sign out** on another row → `DELETE /profile/sessions/{id}` sets `revoked_at`.
3. That device's next request (or token refresh) hits `get_current_user`/`refresh`, the session is invalid → 401 → it's logged out.

## Error handling

- Revoking a session that isn't the caller's → 404 (no enumeration of others' ids).
- Missing/invalid/`sid`-less access token → 401 (existing `_UNAUTHORIZED`).
- Session DB lookup is required (not best-effort) in `get_current_user`; a decode/lookup failure is 401, not a 500.
- `record_activity` stays best-effort (unchanged).

## Testing

**Backend (pytest):**
- Login (no-2FA and post-2FA-verify) creates exactly one valid `AuthSession`; access token carries its `sid`.
- A request with a valid access token whose session was revoked → 401.
- `/auth/refresh` succeeds for a valid session and bumps `last_seen_at`; fails 401 after revoke/expiry.
- `/auth/logout` revokes the current session; subsequent use of that access token → 401.
- `GET /profile/sessions` returns only the caller's valid sessions and flags `current`; never leaks `sid`.
- `DELETE /profile/sessions/{id}`: revokes own; 404 for another user's id.
- `POST /profile/sessions/revoke-others` revokes all but current.
- `POST /admin/users/{id}/revoke-sessions` (admin only; `require_write`/`require_admin` gate).

**Web (vitest):** `SignedInDevicesCard` renders rows, tags current, disables its Sign out, shows "sign out others" only when >1; the 2FA toggle reflects status and triggers enroll/disable; the banner shows only for a not-enrolled/not-prompted user and dismiss hides it.

## Deploy

1. Apply the migration to the **direct** (non-`-pooler`) Neon host (additive; before deploy).
2. Merge to `main`, **push** to `origin/main` → Vercel builds and deploys.
3. Everyone re-logs in once (old `sid`-less tokens rejected).
4. Add `auth_sessions` to the restore-drill `EXPECTED` table list (now 14 tables) and the Backups wiki count.

## Docs to update after build

README/backend README (test counts), wiki `Testing.md`, `Database.md` (new table + ER), `Backups-and-Recovery.md` + `restore-drill.yml` (table count), `iOS-App.md`/`Home.md` security bullets if they enumerate session features.
