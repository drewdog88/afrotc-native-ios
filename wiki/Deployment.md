<div align="center">

# ▲ Deployment

**Web + API ship together on Vercel; data lives in Neon.**

![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=flat-square&logo=neon&logoColor=black)
![Python](https://img.shields.io/badge/Serverless_Python-3776AB?style=flat-square&logo=python&logoColor=white)

</div>

iOS is distributed separately (see [iOS App](iOS-App)).

## One Vercel project, two things

The repo-root `vercel.json` builds the web bundle **and** wires the API as a Python serverless function. Requests split at the edge:

```mermaid
flowchart TD
    REQ(["🌐 Incoming request"]) --> Q{"path matches<br>/api/(.*) ?"}
    Q -->|"Yes"| PY["rewrite → /api/index<br>@vercel/python"]
    PY --> APP["⚙️ FastAPI app<br>api/index.py puts backend/ on path"]
    APP --> DB[("🗄️ Neon Postgres<br>pooled URL")]
    Q -->|"No"| SPA["rewrite → /index.html<br>SPA fallback"]
    SPA --> BUNDLE["🌐 web/dist static bundle"]

    REQ -.->|"every response"| HDR["🔒 Security headers<br>CSP · HSTS · X-Frame-Options"]

    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    class Q,HDR edge
    class PY,APP api
    class SPA,BUNDLE web
    class DB db
```

- **Build**: `installCommand` `cd web && npm install`, `buildCommand` `cd web && npm run build`, `outputDirectory` `web/dist`, `framework: null`.
- **Rewrites**:
  - `/api/(.*)` → `/api/index` — the FastAPI app, run via `@vercel/python`. `api/index.py` puts `backend/` on the path and exposes `app`. Its Python deps come from the root `requirements.txt` (pinned resolved versions).
  - `/((?!api/).*)` → `/index.html` — SPA fallback so client-side routes work.

## Security headers

Set on every response in `vercel.json`:

- **CSP** — `default-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`, `script-src 'self'`; allowances for Google Fonts (style/font) and CARTO basemaps (`img-src` / `connect-src https://*.basemaps.cartocdn.com`) for the MapLibre Territory view; `worker-src`/`child-src blob:`.
- **HSTS** `max-age=63072000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, a restrictive `Permissions-Policy`, and `Cross-Origin-Opener-Policy: same-origin`.

## Environment (set in the Vercel dashboard, never in the repo)

- `DATABASE_URL` — the Neon **pooled** connection string (`…-pooler…?sslmode=require`, driver `postgresql+psycopg://`).
- `SECRET_KEY`, `ENCRYPTION_KEY` — JWT signing and TOTP-secret encryption.
- `BOOTSTRAP_ADMIN_*` — first-run admin seed (only used when `users` is empty).
- `CORS_ORIGINS`, `CRON_SECRET`, and the storage/upload settings as needed.

Migrations are **not** run by the build — apply Alembic against the **direct** (non-pooled) host before/after deploy as needed (see [Database](Database)).

## Deploy flow

```mermaid
flowchart LR
    PUSH(["git push → main"]) --> VB["▲ Vercel builds<br>web/dist + Python fn"]
    VB --> LIVE["🌐 Live deployment"]
    LIVE --> PROMO{"Promote a<br>restored DB?"}
    PROMO -->|"repoint DATABASE_URL (pooled)<br>+ redeploy"| LIVE

    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    class PUSH,PROMO edge
    class VB,LIVE web
```

Vercel builds on push to the connected branch. To promote a restored database, repoint `DATABASE_URL` (pooled) and redeploy — see [Backups & Recovery](Backups-and-Recovery).

> **Neon branch hygiene:** the Neon–Vercel integration can create a database branch per preview deploy. Prune stale per-deploy branches periodically (and consider disabling auto-branch creation) from the Neon console to keep the project tidy on the free plan.
