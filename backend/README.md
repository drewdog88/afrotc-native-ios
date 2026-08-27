<div align="center">

# ⚙️ AFROTC Det 695 — Backend (FastAPI)

**Headless JSON API that powers both the React web app and the SwiftUI iOS app.**

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2.0-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-E92063?style=flat-square&logo=pydantic&logoColor=white)
![Postgres](https://img.shields.io/badge/Neon_Postgres-00E599?style=flat-square&logo=postgresql&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-183_passing-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

</div>

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · JWT (python-jose) · bcrypt · revocable server-side sessions · Resend (email-2FA codes) · Neon PostgreSQL. *(`pyotp` + Fernet are retained as a dormant TOTP scaffold — email is the only active 2FA method.)*

## Request lifecycle

```mermaid
flowchart LR
    REQ(["HTTPS request<br>+ Bearer JWT"])
    AUTH{"get_current_user<br>valid token?"}
    ROLE{"require_write /<br>require_admin?"}
    ROUTE["/api/v1 route<br>Pydantic-validated"]
    DB[("Neon Postgres")]
    OK(["JSON response"])
    E401(["401"])
    E403(["403"])

    REQ --> AUTH
    AUTH -->|no| E401
    AUTH -->|yes| ROLE
    ROLE -->|viewer on mutation| E403
    ROLE -->|allowed| ROUTE
    ROUTE --> DB --> OK

    classDef api fill:#2f9bd8,stroke:#1d6fa0,color:#ffffff
    classDef db fill:#00E599,stroke:#00996a,color:#04321f
    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    class ROUTE api
    class DB db
    class AUTH,ROLE edge
```

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

> **⚠️ Deploying a migration to prod is a manual step.** Vercel ships code only —
> it does **not** run Alembic. A deploy that adds a migration leaves the prod DB a
> revision behind, which surfaces as a **500** (`psycopg.errors.UndefinedTable`)
> the first time an endpoint touches the new table/column. After merging a
> migration, run it against the **direct** (non-pooled) Neon host with the
> `postgresql+psycopg://` driver:
> ```bash
> DATABASE_URL='postgresql+psycopg://USER:PW@HOST.neon.tech/neondb?sslmode=require' \
>   uv run alembic upgrade head   # then confirm: alembic current == alembic heads
> ```
> Full runbook: [Deployment wiki page](https://github.com/drewdog88/afrotc-native-ios/wiki/Deployment).

## Layout
```
app/
  core/       config, database, security (hashing/JWT/encryption)
  models/     SQLAlchemy 2.0 ORM models
  api/v1/     route modules (auth, recruits, cadets, contacts, events, …)
  bootstrap.py first-run admin seed
  main.py     FastAPI app + health
tests/        183 pytest tests over an in-memory SQLite harness
```

## Tests

```bash
uv run pytest -q        # 183 passing — every /api/v1 module
uv run ruff check .     # lint
```

The suite runs against an in-memory SQLite database (via a `get_db` override in
`tests/conftest.py`), so no live Postgres is needed. See the
[Testing wiki page](https://github.com/drewdog88/afrotc-native-ios/wiki/Testing).
