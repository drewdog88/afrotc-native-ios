# iOS ↔ Web Feature Parity Audit

**Date:** 2026-07-12
**Goal:** The iOS native app must reach 100% feature parity with the web app.
**Method:** Every web page diffed against its iOS counterpart (pages, fields,
actions, filters, states). This is the authoritative gap list — work items get
checked off here as they land.

## Headline

**Overall parity ≈ 78%.** Three entire web screens still have no iOS equivalent, and
several screens that *do* exist are missing sub-features (create/edit/delete,
charts, calendar, item counts, geocoding, richer empty/error/loading states).

## Tier 1 — Entire screens missing on iOS

| Web screen | What it does | iOS |
|---|---|---|
| **Admin** (`Admin.tsx`) | Admin-gated user management (list/search, add user, role picker, active toggle, delete) + paginated activity/audit log | ✅ **done** — `AdminView` in the More hub (admin-gated): Users/Activity segmented console, searchable user list with inline role menu + active toggle + swipe-delete (self-row guarded), "Add user" sheet, activity log with 25-row "Load more" |
| **Profile** (`Profile.tsx`) | View/edit profile (name/email/phone), change password, full 2FA/TOTP lifecycle (setup → verify → disable) | ✅ **done** — `ProfileView` in the More hub (view/edit, change password, 2FA copyable secret + URI, Sign Out) |
| **Bulk import** (`ImportRecruits.tsx`) | 3-step CSV/Excel wizard: upload → per-row review (success/fail + errors) → summary | ❌ none |
| **Forgot password** (`ForgotPassword.tsx`) | Security-question reset flow (identify → answer → new password) | ❌ none (users locked out can't self-recover) |
| **Territory** (`Territory.tsx`) | Map of geocoded contacts + events with synced list | ❌ none (design already drafted: `2026-07-12-ios-territory-map-design.md`) |

**Also missing / not surfaced:**
- ✅ **Sign out** — now surfaced as a destructive footer button in `ProfileView` (confirmation dialog → `Session.logout()`).
- ✅ **Profile/Settings entry point** — `.profile` destination ("Profile & Security") added to the More hub.
- ✅ **Admin gating** — `UserOut.isAdmin` now gates the `.admin` More-hub row (dropped entirely for non-admins) and `AdminView` shows a restricted notice as a defensive fallback.

## Tier 2 — Screens that exist but lack sub-features

### Dashboard (~60%)
- ❌ "New recruits" trend area chart (SVG w/ gradient, tooltip)
- ❌ Commission-rate % note on Commissioned tile
- ❌ "needs attention" note on Open follow-ups tile
- ❌ Per-stage conversion % in funnel + stage blurbs
- ❌ Skeleton loading states (uses plain spinner)

### Pipeline (~55%)
- ⚠️ Multi-series cumulative chart renders, but no hover crosshair / multi-series tooltip
- ❌ Interactive legend (web: click stage → `/recruits?stage=`)
- ❌ Clickable conversion-table rows → filtered recruits
- ❌ Stage blurbs in conversion table
- ❌ Page subtitle, skeleton loader

### Follow-ups (~70%)
- ❌ Overdue banner ("N past due — knock these out first")
- ❌ Always-render Overdue/Today groups w/ "caught up" placeholder
- ❌ Relative due labels ("in 3 days", "2 days overdue")
- ❌ Default due = today 5pm (iOS uses now)
- ❌ Inline empty-state "New follow-up" button, skeletons
- ✅ iOS *adds* swipe actions + delete confirmation (web lacks these)

### Recruits (~58%)
- ❌ Chip-style stage filter (iOS uses a Menu)
- ❌ School-type column; result-count footer ("X of Y")
- ❌ Starting-stage picker on create (iOS hardcodes `lead`)
- ❌ Stage change **with note** + stage-change error display; disable current stage
- ❌ Distinct "no recruits yet" vs "no matches" empty states
- ❌ Delete confirmation naming the recruit
- ⚠️ Note: iOS has GPA/interests on create that web lacks — reconcile direction

### Cadets (~70%)
- ❌ Chip-style status filter; rank/major/grad-year columns; result-count footer
- ❌ Delete confirmation naming the cadet; richer empty states
- ⚠️ Status shown as colored text vs web StatusPill component

### Contacts (~62%)
- ❌ Search by email; email column; contact title in row
- ❌ Latitude/longitude display + geocoding trigger
- ❌ Item-count footer; distinct filtered empty state; skeletons
- ⚠️ iOS uses sheet edit vs web inline (acceptable platform difference)

### Events (~58% → ✅ calendar done)
- ✅ **Calendar view** — month grid (6-week/42-cell), color-coded event pills (status dot + title, "+N more" overflow), today highlighted in amber, faded out-of-month days, prev/next/Today nav, Calendar/List segmented toggle. Pills + list rows both push the detail.
- ❌ Save-success indicator; styled date chip in rows; skeletons (Tier-2 polish → item #7)

### Materials (~38% → ✅ done)
- ✅ **Full CRUD.** Document upload (`.fileImporter` → multipart) + swipe-delete; link create/edit/delete via sheet + swipe actions
- ✅ Write-gated to non-viewer roles (matches web `canWrite`); category field; description display; item-count footer
- ✅ Distinct "nothing yet" vs "no matches" empty states
- ✅ Download works (→ iOS share sheet)

## Platform differences that are acceptable (not gaps)
- Apple Maps deep-link instead of Google Maps.
- Sheet-based edit instead of inline edit panels.
- Share-sheet download instead of browser download.
- Swipe actions / confirmation dialogs (iOS-native affordances).

These should be a deliberate, documented choice — everything else should reach parity.

## Suggested sequencing (by user impact)
1. **Sign out button + Profile screen** (account basics; logout already half-built).
2. **Materials CRUD** (biggest single-screen deficit; backend endpoints exist).
3. **Events calendar view** (major UX gap).
4. **Admin console** (user mgmt + activity log).
5. **Territory map** (design ready).
6. **Bulk import**, **Forgot password**.
7. **Within-screen polish**: chip filters, result counts, richer empty/error/skeleton states, stage-change-with-note, dashboard/pipeline chart depth.

Each item becomes its own spec → plan → implement cycle, checked off above.
