# iOS ↔ Web Feature Parity Audit

**Date:** 2026-07-12
**Goal:** The iOS native app must reach 100% feature parity with the web app.
**Method:** Every web page diffed against its iOS counterpart (pages, fields,
actions, filters, states). This is the authoritative gap list — work items get
checked off here as they land.

## Headline

**Overall parity ≈ 100%.** Every top-level web screen has an iOS equivalent
(Tier 1 ✅) and every Tier-2 within-screen gap — charts, chip filters, result
counts, richer empty/error/skeleton states, stage-change-with-note, dashboard
and pipeline chart depth — has been closed. What remains are the deliberate,
documented platform differences below (Apple Maps, sheet edits, share-sheet
downloads, swipe actions).

## Tier 1 — Entire screens (all now have iOS equivalents ✅)

| Web screen | What it does | iOS |
|---|---|---|
| **Admin** (`Admin.tsx`) | Admin-gated user management (list/search, add user, role picker, active toggle, delete) + paginated activity/audit log | ✅ **done** — `AdminView` in the More hub (admin-gated): Users/Activity segmented console, searchable user list with inline role menu + active toggle + swipe-delete (self-row guarded), "Add user" sheet, activity log with 25-row "Load more" |
| **Profile** (`Profile.tsx`) | View/edit profile (name/email/phone), change password, full 2FA/TOTP lifecycle (setup → verify → disable) | ✅ **done** — `ProfileView` in the More hub (view/edit, change password, 2FA copyable secret + URI, Sign Out) |
| **Bulk import** (`ImportRecruits.tsx`) | 3-step CSV/Excel wizard: upload → per-row review (success/fail + errors) → summary | ✅ **done** — `ImportRecruitsView`, reached from the Recruits "Add" menu (write-gated): stepper (Upload/Review/Done), `.fileImporter` for .csv/.xlsx/.xls with expected-columns hint, submits to `/recruits/import`, per-row error list + imported/skipped/total summary, reloads roster on success |
| **Forgot password** (`ForgotPassword.tsx`) | Security-question reset flow (identify → answer → new password) | ✅ **done** — `ForgotPasswordView` sheet from the login screen: identify (username/email → security question) → answer + new password → done, clears lockout |
| **Territory** (`Territory.tsx`) | Map of geocoded contacts + events with synced list | ✅ **done** — `TerritoryView` in the More hub: native MapKit map with kind-tinted pins (contacts amber / events green), draggable bottom sheet (filter chips w/ counts, located-places list, missing-coords footnote), pin↔row selection sync + fly-to, "Open" pushes existing Contact/Event detail |

**Also missing / not surfaced:**
- ✅ **Sign out** — now surfaced as a destructive footer button in `ProfileView` (confirmation dialog → `Session.logout()`).
- ✅ **Profile/Settings entry point** — `.profile` destination ("Profile & Security") added to the More hub.
- ✅ **Admin gating** — `UserOut.isAdmin` now gates the `.admin` More-hub row (dropped entirely for non-admins) and `AdminView` shows a restricted notice as a defensive fallback.

## Tier 2 — Screens that exist but lack sub-features

### Dashboard (~60% → ✅ done)
- ✅ "New recruits" trend area chart — Swift `Charts` AreaMark+LineMark w/ accent gradient, week-bucketed x axis, empty-state copy
- ✅ Commission-rate % note ("N% of pipeline") on Commissioned tile
- ✅ "needs attention" / "all clear" note on Open follow-ups tile
- ✅ Per-stage conversion % (vs stage below) + stage blurbs in the Ascent funnel
- ✅ Page title + subtitle ("Detachment overview" / "Live recruiting pipeline…")
- ✅ Redacted skeleton tiles + panels while the first load is in flight (was plain spinner)

### Pipeline (~55% → ✅ done)
- ✅ Hover crosshair + multi-series tooltip on the cumulative chart (`.chartXSelection` + `.chartBackground` proxy crosshair + per-stage tooltip overlay sorted by funnel order)
- ✅ Chronologically-sorted x-axis (`.chartXScale(domain:)`) so cumulative lines climb left→right instead of crisscrossing
- ✅ Interactive legend — tappable stage capsules → `router.openRecruits(stage:)` (mirrors web click stage → `/recruits?stage=`)
- ✅ Clickable conversion-table rows → filtered recruits (same drill-through)
- ✅ Stage blurbs in the conversion table
- ✅ Page title + subtitle + redacted skeleton loader (was a plain overlay spinner)

### Follow-ups (~70% → ✅ done)
- ✅ Overdue banner ("N past due — knock these out first")
- ✅ Overdue/Today groups always render with "caught up" / "nothing due today" placeholder; Upcoming/Done hidden when empty
- ✅ Relative due labels ("today"/"tomorrow"/"N days overdue"/"in N days")
- ✅ Default due = today 5pm (was now)
- ✅ Inline empty-state "New follow-up" button + richer copy
- ✅ iOS *adds* swipe actions + delete confirmation (web lacks these)

### Recruits (~58% → ✅ done)
- ✅ Chip-style stage filter row (All + each stage, tinted via Theme.stageColor) replacing the Menu
- ✅ School-type shown in row ("current_school · HS/College"); result-count footer ("N of M recruits")
- ✅ Starting-stage picker on create (was hardcoded `lead`)
- ✅ Stage change **with note** via `StageChangeSheet` (current stage disabled) + stage-change error display
- ✅ Distinct "No matches" vs "No recruits yet" empty states
- ✅ Delete confirmation naming the recruit
- ✅ "Import from file" added to the Add menu (write-gated) → `ImportRecruitsView`
- ⚠️ Note: iOS has GPA/interests on create that web lacks — reconcile direction

### Cadets (~70% → ✅ done)
- ✅ Chip-style status filter (All + active/inactive/graduated, tinted); rank · major · 'grad-year row subtitle; result-count footer ("N of M cadets")
- ✅ Delete confirmation naming the cadet; distinct "No matches" vs "No cadets yet" empty states
- ✅ `CadetStatusPill` tinted-capsule component in rows + detail (was plain colored text)

### Contacts (~62% → ✅ done)
- ✅ Search by name/school/email (backend `search` covers email); email + contact title now shown in the row
- ✅ Latitude/longitude shown in detail alongside the Map link (geocoding runs server-side; no manual trigger needed)
- ✅ Result-count footer ("N of M contacts"); distinct "No matches" vs "No contacts yet" empty states
- ✅ Chip-style status filter row (All / Active / Inactive) replacing the Menu; delete confirmation names the contact
- ⚠️ iOS uses sheet edit vs web inline (acceptable platform difference)

### Events (~58% → ✅ done)
- ✅ **Calendar view** — month grid (6-week/42-cell), color-coded event pills (status dot + title, "+N more" overflow), today highlighted in amber, faded out-of-month days, prev/next/Today nav, Calendar/List segmented toggle. Pills + list rows both push the detail.
- ✅ Styled month/day `EventDateChip` in list rows (mirrors web `dateChip`) + tinted `EventStatusPill` on each row
- ✅ Save-success indicator ("Saved" flash) in `EventFormSheet` before the sheet dismisses

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
