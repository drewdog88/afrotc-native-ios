<div align="center">

# 🎖️ AFROTC Detachment 695 — Recruiting Platform

**One product, three surfaces, one database.** A recruiting and cadet-management
platform for **AFROTC Detachment 695** (University of Portland), covering the
Pacific Northwest.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![Swift](https://img.shields.io/badge/SwiftUI-F05138?style=flat-square&logo=swift&logoColor=white)
![Postgres](https://img.shields.io/badge/Neon_Postgres-00E599?style=flat-square&logo=postgresql&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)
![Tests](https://img.shields.io/badge/pytest-95_passing-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

</div>

| Surface | Stack | Directory |
|---|---|---|
| **Backend** | FastAPI · SQLAlchemy 2.0 · Neon Postgres | [`backend/`](backend/) |
| **Web** | React 19 · TypeScript · Vite · Vercel | [`web/`](web/) |
| **iOS** | SwiftUI · XcodeGen | [`ios/`](ios/) |

All three talk to the **same Neon Postgres database through the same API
contract** ([`shared/openapi.json`](shared/openapi.json)) — a data edit shows up
everywhere at once. Full documentation is in the
**[project wiki](https://github.com/drewdog88/afrotc-native-ios/wiki)**.

```mermaid
flowchart TD
    WEB["🌐 Web<br>React 19 · Vite"]
    IOS["📱 iOS<br>SwiftUI"]
    CONTRACT{{"📄 shared/openapi.json<br>one API contract"}}
    API["⚙️ FastAPI service<br>auth · recruiting · analytics"]
    DB[("🐘 Neon Postgres<br>the only datastore")]

    WEB & IOS -->|"HTTPS + Bearer JWT"| API
    WEB -.generated types.-> CONTRACT
    IOS -.mirrored models.-> CONTRACT
    CONTRACT -.describes.-> API
    API --> DB

    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef ios fill:#0c1c33,stroke:#050d1a,color:#ffffff
    classDef api fill:#2f9bd8,stroke:#1d6fa0,color:#ffffff
    classDef db fill:#00E599,stroke:#00996a,color:#04321f
    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    class WEB web
    class IOS ios
    class API api
    class DB db
    class CONTRACT edge
```

## Quickstart

Run all three locally (backend on 8099 so the iOS simulator finds it):

```bash
# 1. Backend  (needs a Neon DATABASE_URL — there is no local DB fallback)
cd backend && cp .env.example .env      # set DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY, BOOTSTRAP_ADMIN_PASSWORD
uv sync --extra dev
uv run alembic upgrade head             # create schema (direct, non-pooled host)
uv run uvicorn app.main:app --reload --port 8099

# 2. Web
cd web && npm install && npm run dev     # http://localhost:5173

# 3. iOS
cd ios && xcodegen generate && open Det695.xcodeproj   # ⌘R
```

Log in with the demo admin `admin` / `Det695Demo!`.

## Documentation

| Page | What it covers |
|---|---|
| [Architecture](https://github.com/drewdog88/afrotc-native-ios/wiki/Architecture) | How the three surfaces fit together |
| [Backend API](https://github.com/drewdog88/afrotc-native-ios/wiki/Backend-API) | FastAPI service, endpoints, auth, config |
| [Web App](https://github.com/drewdog88/afrotc-native-ios/wiki/Web-App) · [iOS App](https://github.com/drewdog88/afrotc-native-ios/wiki/iOS-App) | The two clients |
| [Database](https://github.com/drewdog88/afrotc-native-ios/wiki/Database) | Neon Postgres, schema, migrations, seeding |
| [Backups & Recovery](https://github.com/drewdog88/afrotc-native-ios/wiki/Backups-and-Recovery) · [`BACKUP.md`](BACKUP.md) | Nightly dumps, restore drill, runbook |
| [Deployment](https://github.com/drewdog88/afrotc-native-ios/wiki/Deployment) | How web + API ship to Vercel |
| [Development Process](https://github.com/drewdog88/afrotc-native-ios/wiki/Development-Process) · [Testing](https://github.com/drewdog88/afrotc-native-ios/wiki/Testing) · [Roadmap](https://github.com/drewdog88/afrotc-native-ios/wiki/Roadmap) | Working on it |

## Ground rules

- **Neon Postgres is the only runtime datastore** — no local/SQLite fallback.
- **Data is real and Pacific-Northwest** — never seed out-of-region records.
- **Secrets never land in the repo** — `.env` locally; Vercel / GitHub Actions
  secrets in the cloud.

## Repository layout

```
backend/   FastAPI service, models, Alembic migrations, scripts, tests
web/       React + TypeScript + Vite app (deploys to Vercel)
ios/       SwiftUI app (XcodeGen-generated project)
shared/    openapi.json — the contract both clients build against
wiki/      documentation source (synced to the GitHub Wiki)
.github/   backup + restore-drill workflows
BACKUP.md  disaster-recovery runbook
```
