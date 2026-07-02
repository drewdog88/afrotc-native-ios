# AFROTC Det 695 — Backend (FastAPI)

Headless JSON API that powers both the React web app and the SwiftUI iOS app.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · JWT (python-jose) · passlib/bcrypt · Neon PostgreSQL (SQLite for local dev).

## Quickstart

```bash
cd backend
cp .env.example .env          # then edit SECRET_KEY, ENCRYPTION_KEY, BOOTSTRAP_ADMIN_PASSWORD
uv sync --extra dev           # create venv + install deps
uv run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive OpenAPI docs.

Local dev uses a SQLite file (`afrotc695.db`) by default and auto-creates the
schema on startup. Point `DATABASE_URL` at Neon to use Postgres (migrations via
Alembic).

## Layout
```
app/
  core/       config, database, security (hashing/JWT/encryption)
  models/     SQLAlchemy 2.0 ORM models
  bootstrap.py first-run admin seed
  main.py     FastAPI app + health
```
