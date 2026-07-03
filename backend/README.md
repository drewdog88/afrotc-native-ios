# AFROTC Det 695 — Backend (FastAPI)

Headless JSON API that powers both the React web app and the SwiftUI iOS app.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · JWT (python-jose) · bcrypt · pyotp (TOTP) · Neon PostgreSQL.

## Quickstart

```bash
cd backend
cp .env.example .env          # then edit DATABASE_URL (Neon), SECRET_KEY, ENCRYPTION_KEY, BOOTSTRAP_ADMIN_PASSWORD
uv sync --extra dev           # create venv + install deps
uv run alembic upgrade head   # create the schema (against the direct, non-pooled Neon host)
uv run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive OpenAPI docs.

**Postgres only — no local/SQLite fallback.** `DATABASE_URL` must be a
`postgresql` URL (the config validator rejects anything else). The schema is owned
entirely by Alembic; the app never auto-creates tables. See the
[Database wiki page](https://github.com/drewdog88/afrotc-native-ios/wiki/Database).

## Layout
```
app/
  core/       config, database, security (hashing/JWT/encryption)
  models/     SQLAlchemy 2.0 ORM models
  bootstrap.py first-run admin seed
  main.py     FastAPI app + health
```
