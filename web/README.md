<div align="center">

# 🌐 AFROTC Det 695 — Web (React + TypeScript + Vite)

**The browser client for the Det 695 recruiting platform.** It shares the API
contract (`../shared/openapi.json`) with the SwiftUI iOS app, so the two read as
one product.

![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite_8-646CFF?style=flat-square&logo=vite&logoColor=white)
![TanStack Query](https://img.shields.io/badge/TanStack_Query-FF4154?style=flat-square&logo=reactquery&logoColor=white)
![MapLibre](https://img.shields.io/badge/MapLibre-396CB2?style=flat-square&logo=maplibre&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

</div>

## Stack

React 19 · React Router 7 · TanStack Query · Vite 8 · TypeScript · oxlint ·
MapLibre GL (Territory map). API types are generated from the OpenAPI contract
via `openapi-typescript` into `src/api/schema.d.ts`.

## Run locally

```bash
npm install
npm run dev        # Vite dev server → http://localhost:5173
```

Run the backend alongside it (`cd ../backend && uv run uvicorn app.main:app
--port 8000`). The API base defaults to `/api/v1`; override with the
`VITE_API_BASE` env var. Log in with the demo admin `admin` / `Det695Demo!`.

```bash
npm run build      # tsc -b && vite build → dist/
npm run lint       # oxlint
```

## Layout

```
src/
  main.tsx          entry: React Query + Router + AuthProvider + routes
  lib/              api.ts (fetch + Bearer JWT + refresh), auth.tsx, stages.ts
  api/schema.d.ts   generated OpenAPI types (keep in sync with the backend)
  components/       AppShell, Insignia (the Det 695 crest), StageChip, TrendArea
  pages/            Login, Dashboard, Recruits, RecruitDetail, Cadets, Contacts,
                    Pipeline, Events, EventDetail, FollowUps, Materials,
                    Territory, ImportRecruits, Profile, Admin
  styles/tokens.css design tokens (mirrored into the iOS Theme)
```

## Regenerate the API types after a backend change

```bash
cd ../backend && uv run python scripts/export_openapi.py
cd ../web && npx openapi-typescript ../shared/openapi.json -o src/api/schema.d.ts
```

## Deploy

Ships to Vercel from the repo-root `vercel.json` (build `cd web && npm run
build`, output `web/dist`; `/api/*` → a Python serverless FastAPI function; SPA
fallback to `index.html`; hardened security headers). See the
[Deployment wiki page](https://github.com/drewdog88/afrotc-native-ios/wiki/Deployment).
