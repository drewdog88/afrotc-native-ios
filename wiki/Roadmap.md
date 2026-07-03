# Roadmap

Where the platform is and what's next. Not a promise — a living list.

## Done

- Three-surface product live: **FastAPI backend + React/Vite web + SwiftUI iOS**,
  one Neon Postgres, one OpenAPI contract.
- Full recruiting workflow: recruits with an append-only stage funnel, cadets,
  university contacts, events, follow-ups, and a Materials library (links +
  documents stored as Postgres `bytea`).
- Analytics: funnel, trends, and a dashboard stats endpoint feeding both clients.
- Territory map (MapLibre + CARTO) over geocoded PNW schools/contacts.
- Security: JWT auth with refresh, bcrypt passwords with lockout/history/expiry,
  Fernet-encrypted TOTP 2FA, activity log, and a hardened CSP + header set on
  Vercel.
- Data protection: nightly `pg_dump` → GitHub Release backups and a weekly
  automated restore drill.
- Web + iOS both carry the real Detachment 695 crest.

## Next

- **Automated tests.** The pytest toolchain is wired but empty — add API tests
  (auth, funnel, materials, import, admin guardrails) and iOS/web coverage. See
  [Testing](Testing).
- **Docs hygiene.** Root README + per-surface READMEs kept current; retire the
  leftover Vite starter template content in `web/`.
- **Neon branch hygiene.** Prune per-deploy Neon branches and consider disabling
  auto-branch creation in the Neon–Vercel integration to stay tidy on the free
  plan.

## Later / ideas

- Richer analytics (per-recruiter, per-school conversion; event ROI).
- Push notifications / reminders for due follow-ups on iOS.
- iOS parity for the pages that are currently web-only (Contacts detail, Events
  detail, Admin).
- App Store / TestFlight distribution pipeline for the iOS client.

## Non-goals / constraints

- **No paid infrastructure** unless clearly justified — free Neon + Vercel +
  GitHub Actions is the operating envelope (Vercel Blob is acceptable if needed).
- **Postgres is the only runtime datastore** — no local/SQLite fallback.
- **Pacific-Northwest data only** — never fabricate out-of-region records.
