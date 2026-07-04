<div align="center">

# 🧭 Architecture

**Three clients. One API. One database.**

![React](https://img.shields.io/badge/Web-61DAFB?style=flat-square&logo=react&logoColor=black)
![Swift](https://img.shields.io/badge/iOS-F05138?style=flat-square&logo=swift&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-009688?style=flat-square&logo=fastapi&logoColor=white)
![Neon](https://img.shields.io/badge/Neon_Postgres-00E599?style=flat-square&logo=neon&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

</div>

## The system, end to end

```mermaid
flowchart TB
    subgraph edge["📱🌐  Client tier"]
        direction LR
        WEB["🌐 Web (React)<br>Vercel-hosted SPA<br>browser storage"]
        IOS["📱 iOS (SwiftUI)<br>iPhone<br>Keychain-stored JWT"]
    end

    subgraph vercel["▲  Vercel project"]
        direction TB
        STATIC["Static bundle<br>web/dist"]
        API["⚙️ Backend (FastAPI)<br>SQLAlchemy 2.0<br>/api/v1/* · OpenAPI at /docs<br>Python serverless function"]
    end

    DB[("🗄️ Neon Postgres<br>single source of truth")]

    WEB -->|"HTTPS · static"| STATIC
    WEB -->|"HTTPS / JSON<br>Bearer JWT"| API
    IOS -->|"HTTPS / JSON<br>Bearer JWT"| API
    API -->|"postgresql+psycopg<br>pooled · sslmode=require"| DB

    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef ios fill:#0c1c33,stroke:#000000,color:#ffffff
    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    classDef static fill:#eef2f7,stroke:#d4dde8,color:#33445c
    class WEB web
    class IOS ios
    class API api
    class DB db
    class STATIC static
```

Both clients speak HTTPS/JSON to the same API and carry a Bearer JWT. The web bundle and the API are **one Vercel project**; the database is a single Neon instance. There is no per-client backend and no second copy of the data.

## The shared contract

The backend publishes an OpenAPI schema (browsable at `/docs`, exported to `shared/openapi.json`). **Both clients are generated against that one contract** — so the web app (`web/src/lib/api.ts` + generated `web/src/api/schema.d.ts`) and the iOS app (`ios/Det695/Networking`, `ios/Det695/Models`) speak identical request/response shapes.

```mermaid
flowchart LR
    BE["⚙️ FastAPI routes<br>+ Pydantic schemas"] --> EXPORT["scripts/export_openapi.py"]
    EXPORT --> SPEC{{"📜 shared/openapi.json<br>the contract"}}
    SPEC -->|"openapi-typescript"| TS["🌐 web/src/api/schema.d.ts<br>TypeScript types"]
    SPEC -->|"mirrored by hand"| SW["📱 ios/Det695/Models<br>Codable structs"]

    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef ios fill:#0c1c33,stroke:#000000,color:#ffffff
    class BE,EXPORT api
    class SPEC edge
    class TS web
    class SW ios
```

> Change the API and **both clients change with it.** That is what keeps the two front-ends reading as one product rather than two apps that happen to share a logo.

## Why one database matters

There is exactly one Neon Postgres instance behind everything. An edit made in the web admin, via the API, or through a data migration is instantly visible to every surface — the deployed Vercel API, the browser app, and any phone. There is no per-client cache to reconcile and no local datastore to drift out of sync.

## Auth flow (at a glance)

1. Client `POST`s credentials to `/api/v1/auth/login` and receives a JWT `access_token` (plus a refresh token).
2. The client stores the token — **Keychain** on iOS, browser storage on web — and sends `Authorization: Bearer <token>` on every request.
3. On a 401 the client transparently refreshes and retries, so the user isn't bounced to the login screen mid-session.

Demo admin: `admin` / `Det695Demo!`. **See the full sequence diagrams on [How It Works](How-It-Works).**

## Repository layout

```
afrotc-native-ios/
  backend/     FastAPI service, models, migrations, scripts, tests
  web/         React + TypeScript + Vite app (deploys to Vercel)
  ios/         SwiftUI app (XcodeGen-generated project)
  shared/      openapi.json — the contract both clients build against
  wiki/        this documentation (synced to the GitHub Wiki)
  .github/     backup + restore-drill + sync-wiki workflows
  BACKUP.md    disaster-recovery runbook (see Backups & Recovery)
```

See each surface's page for the internals: [Backend API](Backend-API), [Web App](Web-App), [iOS App](iOS-App), [Database](Database) — and [How It Works](How-It-Works) for the request lifecycle.
