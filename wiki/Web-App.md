<div align="center">

# 🌐 Web App

**The browser client cadre and staff use day to day.**

![React](https://img.shields.io/badge/React_19-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite_8-646CFF?style=flat-square&logo=vite&logoColor=white)
![React Query](https://img.shields.io/badge/TanStack_Query-FF4154?style=flat-square&logo=reactquery&logoColor=white)
![MapLibre](https://img.shields.io/badge/MapLibre-396CB2?style=flat-square&logo=maplibre&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

</div>

**React 19 + TypeScript + Vite**, deployed to Vercel. It shares the API contract with the iOS app.

## Gallery

<div align="center">
<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/01-login.png" alt="Login" /><br><sub><b>Login</b> — the Det 695 crest</sub></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/02-dashboard.png" alt="Dashboard" /><br><sub><b>Dashboard</b> — stats + "The Ascent" funnel</sub></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-recruits.png" alt="Recruits" /><br><sub><b>Recruits</b> — searchable, stage-filtered</sub></td>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-pipeline.png" alt="Pipeline" /><br><sub><b>Pipeline</b> — funnel stage by stage</sub></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-map.png" alt="Territory map" /><br><sub><b>Territory</b> — geocoded PNW map</sub></td>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-cadets.png" alt="Cadets" /><br><sub><b>Cadets</b> — active / inactive / graduated</sub></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-contacts.png" alt="Contacts" /><br><sub><b>Contacts</b> — schools &amp; POCs</sub></td>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-events.png" alt="Events" /><br><sub><b>Events</b> — outreach calendar</sub></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-follow-ups.png" alt="Follow-ups" /><br><sub><b>Follow-ups</b> — tasks by assignee</sub></td>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-materials.png" alt="Materials" /><br><sub><b>Materials</b> — links + documents</sub></td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-import.png" alt="Import" /><br><sub><b>Import</b> — CSV / Excel upload</sub></td>
    <td><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-admin.png" alt="Admin" /><br><sub><b>Admin</b> — user management + activity log</sub></td>
  </tr>
</table>
</div>

## Stack

- **React 19** with **React Router 7** for routing and **TanStack Query** (`@tanstack/react-query`) for server state / caching.
- **Vite 8** build, **oxlint** for linting.
- **maplibre-gl** for the recruiting **Territory** map.
- **openapi-typescript** generates `src/api/schema.d.ts` from `shared/openapi.json`, so request/response types are always in lockstep with the backend — the same contract the iOS models mirror.
- CSS Modules per component/page; shared design tokens in `src/styles/tokens.css`.

## How data flows

```mermaid
flowchart LR
    UI["🧩 Page / component"] --> RQ["TanStack Query<br>cache · retry · invalidation"]
    RQ --> API["lib/api.ts<br>fetch wrapper"]
    API -->|"Authorization: Bearer<br>refresh-on-401"| BE["/api/v1/*"]
    SCHEMA{{"schema.d.ts<br>generated from openapi.json"}} -.->|"types"| API
    BE --> DB[("🗄️ Neon")]

    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    class UI,RQ web
    class API,BE api
    class DB db
    class SCHEMA edge
```

## Layout

```
web/src/
  main.tsx            app entry
  App.tsx             routes + providers
  lib/
    api.ts            fetch wrapper (Bearer JWT, refresh on 401)
    auth.tsx          auth context/provider
    stages.ts         recruit-stage helpers
  api/schema.d.ts     generated OpenAPI types
  components/         AppShell, Insignia (the Det 695 crest), StageChip, TrendArea
  pages/              Login, Dashboard, Recruits, RecruitDetail, Cadets, Contacts,
                      Pipeline, Events, EventDetail, FollowUps, Materials,
                      Territory, ImportRecruits, Profile, Admin
  styles/tokens.css   design tokens (mirrored into the iOS Theme)
  assets/             det695-patch.png (the crest), hero.png
```

## Run locally

```bash
cd web
npm install
npm run dev          # Vite dev server (defaults to http://localhost:5173)
```

Point it at a backend via the API base in `src/lib/api.ts` (or its env var) — run the backend with `uv run uvicorn app.main:app --port 8000` alongside it.

```bash
npm run build        # tsc -b && vite build  → web/dist
npm run lint         # oxlint
```

## Branding

`src/components/Insignia.tsx` renders the real **Detachment 695 patch** (`src/assets/det695-patch.png`) — the same crest the iOS app shows — in the rail header and on the login screen. Design tokens (`src/styles/tokens.css`) define the "Flight Line Operations" palette: cool paper by day, command navy by night, with a single amber **beacon** accent for primary actions.

## Deploy

Ships to Vercel from the repo root `vercel.json` (build `cd web && npm run build`, output `web/dist`). SPA routes fall through to `index.html`; `/api/*` is rewritten to a Python serverless function that runs the FastAPI backend. Security headers (CSP, HSTS, `X-Frame-Options: DENY`, etc.) are set there too. See [Deployment](Deployment).
