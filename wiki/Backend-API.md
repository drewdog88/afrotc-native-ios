# Backend API

The headless JSON API that powers both clients. **FastAPI + SQLAlchemy 2.0 +
Neon Postgres.** Interactive OpenAPI docs at `/docs`; the exported contract lives
at `shared/openapi.json`.

## Stack

FastAPI (`>=0.115`) · Uvicorn · SQLAlchemy 2.0 · Alembic · Pydantic v2 /
pydantic-settings · psycopg 3 · python-jose (JWT) · bcrypt · pyotp (TOTP) ·
cryptography (Fernet) · pandas + openpyxl + reportlab (import/export). Python
**≥ 3.11**, managed with **uv**.

## Run it

```bash
cd backend
cp .env.example .env      # set DATABASE_URL (Neon), SECRET_KEY, ENCRYPTION_KEY,
                          # BOOTSTRAP_ADMIN_PASSWORD
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

`http://localhost:8000/docs` for Swagger UI. (The iOS app defaults to port
**8099** — run it there when working with the simulator.)

> **Postgres only.** `config.py` validates `DATABASE_URL` and *rejects* anything
> that isn't a `postgresql` URL — there is no SQLite/local fallback at runtime.
> The schema is owned entirely by Alembic; the app never auto-creates tables. See
> [Database](Database).

## Shape

```
backend/app/
  main.py       FastAPI app, CORS, /health, lifespan → bootstrap_admin
  bootstrap.py  seeds the first admin when the users table is empty
  core/         config (settings), database (engine/session), security (JWT/bcrypt/Fernet)
  api/deps.py   pagination, get_current_user, require_admin
  api/v1/       the routers (below), aggregated in router.py → mounted at /api/v1
  models/       SQLAlchemy 2.0 ORM (see Database)
  schemas/      Pydantic request/response models
  services/     CRUDBase and helpers
```

Meta routes (outside the prefix): `GET /health` → `{"status":"ok"}`, `GET /` →
name + docs link.

## Endpoints (all under `/api/v1`)

Everything requires `Authorization: Bearer <jwt>` except `POST /auth/login` and
`POST /auth/refresh`.

**Auth** (`/auth`)
- `POST /auth/login` — credentials (+ optional TOTP) → access + refresh token pair;
  handles lockout, disabled accounts, forced password change.
- `POST /auth/refresh` — refresh token → new access token.
- `POST /auth/logout` — 204 (stateless; client discards tokens).
- `GET /auth/me` — the current user.
- `POST /auth/change-password` — enforces history-reuse + expiry policy.

**Recruits** (`/recruits`) — the reference CRUD router
- `GET /recruits` — paginated; filters `search`, `stage`, `school_type`.
- `GET|POST|PATCH|DELETE /recruits[/{id}]` — CRUD (create seeds a baseline stage event).
- `POST /recruits/{id}/stage` — change funnel stage; appends an immutable
  `RecruitStageEvent`.
- `GET /recruits/{id}/stage-history` — the stage-change audit trail.
- `POST /recruits/import` — bulk CSV/Excel upload (pandas), per-row validation,
  returns an `ImportResult` with row-level errors.

**Cadets** (`/cadets`), **Contacts** (`/contacts`), **Events** (`/events`) —
standard `GET` (list + filters) / `GET /{id}` / `POST` / `PATCH /{id}` /
`DELETE /{id}`.

**Follow-ups** (`/followups`) — CRUD plus `POST /followups/{id}/complete`. List
filter `assignee_id` accepts `"me"` or a user id, plus `status` and `due_before`.

**Materials** (`/materials`)
- Links: `GET|POST /materials/links`, `PATCH|DELETE /materials/links/{id}`.
- Documents: `GET|POST /materials/documents` (multipart upload, enforces
  `MAX_UPLOAD_BYTES`), `GET /materials/documents/{id}/download` (streamed),
  `DELETE /materials/documents/{id}`.

**Analytics & dashboard**
- `GET /analytics/funnel` — count per stage (respects `FUNNEL_ORDER`), date window.
- `GET /analytics/trends` — time-series of stage transitions (`interval=week|month`).
- `GET /dashboard/stats` — totals, recruits-by-stage, cadets-by-status, open
  follow-ups, ~8-week recruit-created trend.

**Exports** (`/export`) — `GET /export/{entity}?format=csv|xlsx|pdf` for
recruits / cadets / contacts / events.

**Profile** (`/profile`) — get/update profile; 2FA setup / verify / disable (TOTP).

**Admin** (`/admin`, admin-only) — user CRUD (blocks deleting the last admin) and
`GET /admin/activity` (the activity log).

## Auth & security

- **JWT** (HS256, python-jose) signed with `SECRET_KEY`. Access token ~30 min,
  refresh ~14 days; clients refresh once on a 401 and retry.
- **Passwords** hashed with bcrypt. Policy: lockout after `MAX_FAILED_LOGINS`,
  reuse blocked against the last N (`PASSWORD_HISTORY_SIZE`), expiry
  (`PASSWORD_EXPIRY_DAYS`, admins exempt).
- **2FA**: TOTP via pyotp; the secret is **Fernet-encrypted at rest** using
  `ENCRYPTION_KEY` (fails closed if unset).
- **Activity log** records mutating actions for audit.

## Configuration (env vars — no secrets in the repo)

`DATABASE_URL` (required, must be `postgresql`), `SECRET_KEY`, `ENCRYPTION_KEY`,
`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`,
`PASSWORD_EXPIRY_DAYS`, `MAX_FAILED_LOGINS`, `PASSWORD_HISTORY_SIZE`,
`BOOTSTRAP_ADMIN_USERNAME` / `_EMAIL` / `_PASSWORD`, `STORAGE_BACKEND`
(`postgres` default | `vercel_blob`), `BLOB_READ_WRITE_TOKEN`, `MAX_UPLOAD_BYTES`
(25 MB), `CORS_ORIGINS`, `CRON_SECRET`. Locally these live in `.env` (gitignored);
in the cloud they're Vercel env vars / GitHub Actions secrets.

## Document storage

With `STORAGE_BACKEND=postgres` (the default) uploaded documents are stored as
Postgres `bytea` on `recruitment_document.file_data` and streamed back on
download — so **documents are inside the nightly DB dump** ([Backups &
Recovery](Backups-and-Recovery)). A `vercel_blob` path (`blob_url`) is stubbed but
not yet implemented (download from blob returns 501).
