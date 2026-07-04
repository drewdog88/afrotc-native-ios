<div align="center">

# 🛠️ Development Process

**How to run the whole product locally and keep the three surfaces in sync.**

![uv](https://img.shields.io/badge/uv-DE5FE9?style=flat-square&logo=uv&logoColor=white)
![Node](https://img.shields.io/badge/Node_20+-5FA04E?style=flat-square&logo=nodedotjs&logoColor=white)
![Xcode](https://img.shields.io/badge/Xcode_15+-147EFB?style=flat-square&logo=xcode&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=flat-square&logo=neon&logoColor=black)

</div>

## Local topology

```mermaid
flowchart TB
    subgraph mac["💻 Your Mac"]
        BE["⚙️ backend<br>uvicorn :8099"]
        WEBUI["🌐 web<br>vite :5173"]
        SIM["📱 iOS Simulator<br>→ localhost:8099"]
    end
    NEON[("🗄️ Neon Postgres<br>cloud — no local DB")]

    WEBUI --> BE
    SIM --> BE
    BE -->|"pooled · TLS"| NEON

    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef ios fill:#0c1c33,stroke:#000000,color:#ffffff
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    class BE api
    class WEBUI web
    class SIM ios
    class NEON db
```

## Prerequisites

- **uv** (Python ≥ 3.11) for the backend
- **Node 20+** and npm for the web app
- **Xcode 15+** and **XcodeGen** (`brew install xcodegen`) for iOS
- A **Neon Postgres** connection string (there is no local DB fallback)
- Postgres client **≥ 17** for backups/restores (`brew install libpq`)

## Run all three

**1. Backend** (port 8099 so the iOS simulator finds it):

```bash
cd backend
cp .env.example .env        # set DATABASE_URL (Neon), SECRET_KEY, ENCRYPTION_KEY,
                            # BOOTSTRAP_ADMIN_PASSWORD
uv sync --extra dev
uv run alembic upgrade head # first time / after schema changes (direct host)
uv run python scripts/seed_demo.py   # optional: real PNW reference data
uv run uvicorn app.main:app --reload --port 8099
```

**2. Web:**

```bash
cd web && npm install && npm run dev     # http://localhost:5173
```

**3. iOS:**

```bash
cd ios && xcodegen generate && open Det695.xcodeproj   # ⌘R
```

Log in everywhere with `admin` / `Det695Demo!`.

## The contract is the hinge

Both clients build against `shared/openapi.json`. When you change the API, regenerate the contract and propagate it — this loop is what keeps the surfaces in lockstep:

```mermaid
flowchart LR
    CHANGE(["✏️ Change a FastAPI route"]) --> EXPORT["scripts/export_openapi.py"]
    EXPORT --> SPEC{{"📜 shared/openapi.json"}}
    SPEC -->|"npx openapi-typescript"| WEB["🌐 web/src/api/schema.d.ts"]
    SPEC -->|"mirror by hand"| IOS["📱 ios/Det695/Models"]
    WEB --> DONE(["✅ both clients in sync"])
    IOS --> DONE

    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef ios fill:#0c1c33,stroke:#000000,color:#ffffff
    classDef ok fill:#2f8f6b,stroke:#1c6349,color:#ffffff
    class CHANGE,SPEC edge
    class EXPORT api
    class WEB web
    class IOS ios
    class DONE ok
```

```bash
cd backend && uv run python scripts/export_openapi.py   # regenerate the contract
cd ../web && npx openapi-typescript ../shared/openapi.json -o src/api/schema.d.ts
```

Then mirror any new/changed shapes into the iOS `Models/`. Keeping these three in lockstep is what makes the web and iOS apps read as one product.

## Toolchain

- **Backend**: uv, Ruff (lint/format, line length 100, py311), Alembic for schema.
- **Web**: Vite, TypeScript (`tsc -b`), oxlint, `openapi-typescript` codegen.
- **iOS**: XcodeGen (no committed `.xcodeproj` to hand-merge), `xcodebuild`.
- **CI**: GitHub Actions for the nightly backup + weekly restore drill + wiki sync.
- **Hosting**: Vercel (web + serverless API), Neon (Postgres).

## Working rules

- **Commit directly to `main`** — solo repo, `main` is unprotected, no PRs.
- **Never commit secrets.** `.env` / `.env.local` are gitignored; cloud secrets live in Vercel and GitHub Actions.
- **Data is real and Pacific-Northwest.** Seed and reference real Oregon / Washington schools and contacts — never fabricate out-of-region data.
