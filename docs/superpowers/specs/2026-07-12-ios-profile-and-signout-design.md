# Profile & Security + Sign Out (iOS) — Design

**Date:** 2026-07-12
**Status:** Approved
**Parity item:** #1 in `2026-07-12-ios-web-parity-audit.md` (Tier 1 missing screen +
the un-surfaced Sign Out affordance).
**Scope:** Port the web's `Profile.tsx` to a native SwiftUI screen and add the
Sign Out action that exists in code (`Session.logout()`) but was never wired to UI.

## Goal

Give the signed-in user the same self-service account surface the web has:
view/edit profile, change password, and the full two-factor (TOTP) lifecycle —
plus a Sign Out button, which the app currently lacks entirely.

**No backend changes.** Every endpoint already exists and is exercised by the web:

- `GET /profile` — current profile
- `PATCH /profile` — update first/last name, email, phone (`ProfileUpdate`)
- `POST /auth/change-password` — `{ current_password, new_password }`
- `GET /profile/2fa` — `{ enabled }`
- `POST /profile/2fa/setup` — `{ secret, otpauth_uri }`
- `POST /profile/2fa/verify` — `{ code }` → `Message`
- `POST /profile/2fa/disable` → `Message`

`UserOut` (iOS `Auth.swift`) already decodes every field the screen displays
(`firstName`, `lastName`, `email`, `phone`, `username`, `role`, `isAdmin`).

## Why it was missing

Profile is a web-era screen (`web/src/pages/Profile.tsx`, routed `/profile`). The
iOS secondary screens were added in one batch and Profile/account-settings simply
weren't in it. `Session.logout()` was written but never given a button.

## Placement & navigation

A **sixth destination in the More hub** (`MoreView.Destination` in
`RootView.swift`):

- Enum case `profile`; title `"Profile & Security"`; SF Symbol `person.crop.circle`.
- Pushes onto the shared More `NavigationStack` like the other secondary screens.
- `DET695_MORE_DEST=profile` deep-links straight in for CLI capture (the existing
  DEBUG affordance).

Sign Out lives at the **bottom of the Profile screen** as a destructive-role
button with a confirmation dialog — the Settings-app convention iOS users expect,
and where the web keeps account actions too.

## Screen structure

`ProfileView` is a SwiftUI `Form`/`List` with three sections mirroring the web's
three cards, plus a Sign Out footer. It loads via `.task`, seeding from
`session.user` so the first paint has data (mirrors the web's `initialData`).

### 1. Profile (view + edit)
- **View mode:** rows for First name, Last name, Email, Phone; section header
  shows `@username · role`. An **Edit** toolbar button flips the section to edit.
- **Edit mode:** `TextField`s for the four fields with Save / Cancel. Save sends
  a `ProfileUpdate` (trimmed; empty phone → `null`) via `PATCH /profile`, then
  updates the session user and drops back to view mode. Inline status line on
  success/failure.

### 2. Change password
- `SecureField`s: current, new, confirm.
- Client-side guards identical to web: new ≠ confirm → "don't match"; new < 8
  chars → "use at least 8 characters". Only then `POST /auth/change-password`.
- On success clears the fields and shows an inline confirmation.

### 3. Two-factor authentication
- Status badge (Enabled / Disabled) from `GET /profile/2fa`.
- **Disabled → not yet setting up:** explanatory note + "Set up two-factor"
  button → `POST /profile/2fa/setup`.
- **Setup in progress:** show `secret` and `otpauth_uri` as **selectable,
  copyable monospace text** (a "Copy" button on the secret), a note to add it to
  an authenticator app, and a 6-digit code field → `POST /profile/2fa/verify`.
  Cancel abandons setup locally. This matches exactly what the web does — manual
  entry, no QR. (Decision: no QR renderer; keeps the screen dependency-free and
  at parity with the web's actual behavior.)
- **Enabled:** note that the account is protected + "Turn off two-factor" →
  `POST /profile/2fa/disable`.
- Each transition refreshes the 2FA status.

### 4. Sign Out (footer)
- Destructive-role button → `.confirmationDialog` ("Sign out of Det 695?") →
  `await session.logout()`, which clears tokens and flips `phase` to `.signedOut`;
  `RootView` then shows `LoginView`. No new logic — just the button.

## Feedback

The web uses a single auto-dismissing toast. iOS instead surfaces a short inline
status line under each section (success or the `APIError` message) — the
idiomatic pattern for a `Form`, and it keeps each action's result next to its
controls. A submitting action shows a `ProgressView` in place of its button label
and disables the control.

## New surface area

**`ios/Det695/Models/Profile.swift`** (new):
- `struct ProfileUpdate: Encodable` — `firstName`, `lastName`, `email`, `phone`
  (all optional; encoder is `.convertToSnakeCase`).
- `struct TwoFAStatus: Decodable` — `enabled: Bool`.
- `struct TwoFASetupResponse: Decodable` — `secret: String`, `otpauthUri: String`.
- `struct PasswordChangeInput: Encodable` — `currentPassword`, `newPassword`.
- `struct TwoFAVerifyInput: Encodable` — `code: String`.
  (Backend `Message` responses are ignored — the methods return `Void`/throw.)

**`ios/Det695/Networking/APIClient.swift`** (edit) — six methods:
- `func profile() async throws -> UserOut` (`GET /profile`)
- `func updateProfile(_:) async throws -> UserOut` (`PATCH /profile`)
- `func changePassword(_:) async throws` (`POST /auth/change-password`)
- `func twoFAStatus() async throws -> TwoFAStatus` (`GET /profile/2fa`)
- `func twoFASetup() async throws -> TwoFASetupResponse` (`POST /profile/2fa/setup`)
- `func twoFAVerify(_:) async throws` (`POST /profile/2fa/verify`)
- `func twoFADisable() async throws` (`POST /profile/2fa/disable`)

**`ios/Det695/State/Session.swift`** (edit):
- Add `func applyUpdatedUser(_ user: UserOut)` (or make `user` settable from the
  view) so a profile save refreshes the cached user. `logout()` already exists.

**`ios/Det695/Views/RootView.swift`** (edit):
- Add `.profile` to `MoreView.Destination` (title, icon, `navigationDestination`
  branch → `ProfileView()`), and to the `DET695_MORE_DEST` deep-link switch.

**`ios/Det695/Views/ProfileView.swift`** (new) — the screen above.

## States

- **Loading:** seeded from `session.user`; a `ProgressView` only if there's no
  seed and the fetch is in flight.
- **Load error:** `ContentUnavailableView` with the `APIError` description
  ("Couldn't load your profile…").
- **Per-action:** inline status line + disabled/spinner button, as described.

## Testing / verification

Build-and-drive (the iOS project has no unit-test harness):

1. `cd ios && xcodegen generate && xcodebuild` for the booted simulator.
2. Launch with autologin, `DET695_START_TAB=more`, `DET695_MORE_DEST=profile`.
3. Confirm via screenshots:
   - Profile shows the demo admin's details; Edit → change phone → Save persists
     and returns to view mode.
   - Change-password mismatch shows the inline error; a valid change clears fields.
   - 2FA: Set up shows the secret + URI and code field; Disable path shows the
     "off" state. (Verify/enable needs a live TOTP code — confirm the setup UI and
     the disable round-trip; full verify is exercised against a real authenticator.)
   - Sign Out → confirmation → returns to `LoginView`.

## Files

- **New:** `ios/Det695/Views/ProfileView.swift`, `ios/Det695/Models/Profile.swift`
- **Edit:** `ios/Det695/Networking/APIClient.swift`, `ios/Det695/State/Session.swift`,
  `ios/Det695/Views/RootView.swift`

No model changes to `UserOut`, no backend changes.
