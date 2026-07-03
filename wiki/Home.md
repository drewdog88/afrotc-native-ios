# AFROTC Detachment 695 — Recruiting Platform

One product, three surfaces, one database. A recruiting and cadet-management
platform for **AFROTC Detachment 695** (University of Portland) covering the
Pacific Northwest — Seattle, Portland, and campuses across Oregon and Washington.

| Surface | Stack | What it is |
|---|---|---|
| **Backend** | FastAPI · SQLAlchemy 2.0 · Neon Postgres | The headless JSON API. Single source of truth. |
| **Web** | React · TypeScript · Vite · Vercel | The browser app cadre and staff use day to day. |
| **iOS** | SwiftUI · XcodeGen | Native iPhone client, same API contract. |

All three talk to the **same Neon Postgres database through the same API
contract** (`shared/openapi.json`), so a data edit shows up everywhere at once —
prod web, the deployed API, and the phone in your pocket.

## Start here

- **[Architecture](Architecture)** — how the three surfaces fit together
- **[Backend API](Backend-API)** — FastAPI service, endpoints, auth, config
- **[Web App](Web-App)** — the React/Vite client and how it's deployed
- **[iOS App](iOS-App)** — the SwiftUI client and how to build it
- **[Database](Database)** — Neon Postgres, models, migrations, seeding
- **[Backups & Recovery](Backups-and-Recovery)** — nightly dumps, restore drill, runbook
- **[Deployment](Deployment)** — how web + API ship to Vercel
- **[Development Process](Development-Process)** — running all three locally
- **[Testing](Testing)** — what's tested and how to run it
- **[Roadmap](Roadmap)** — what's next

## Ground rules

- **Neon Postgres is the only runtime datastore.** No local/SQLite fallback in
  deployed environments — see [Backups & Recovery](Backups-and-Recovery).
- **Data is real and regional.** Pacific-Northwest schools and contacts only;
  never seed fictitious out-of-region (e.g. California) data.
- **Secrets never land in the repo.** Connection strings and keys live in
  `.env` (gitignored) locally and in Vercel / GitHub Actions secrets in the cloud.
