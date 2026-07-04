<div align="center">

# 🔬 How It Works

**The deep dive.** Follow a single request from a recruiter's phone all the way to a row in Neon Postgres and back — then see how authentication, the recruiting funnel, and bulk import actually behave under the hood.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2.0-CA2A2A?style=flat-square&logo=sqlalchemy&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=flat-square&logo=neon&logoColor=black)

</div>

## Contents

1. [The request flow chart](#1--the-request-flow-chart) — every request, end to end
2. [Authentication sequence](#2--authentication-sequence) — login and the Bearer token
3. [Transparent refresh on 401](#3--transparent-refresh-on-401) — why you're never bounced to login
4. [The recruiting funnel](#4--the-recruiting-funnel-state-machine) — an append-only state machine
5. [The CSV/Excel import pipeline](#5--the-csvexcel-import-pipeline)

---

## 1 · The request flow chart

Every call from either client is the same journey. It enters at the Vercel edge, is routed to either the static web bundle or the FastAPI serverless function, passes an authentication gate (and, for admin routes, an authorization gate), runs a handler that talks to Postgres through SQLAlchemy, and returns JSON. The decision tree below is the whole story on one page.

```mermaid
flowchart TD
    START(["📱 / 🌐 Client fires a request"]) --> EDGE{"▲ Vercel edge<br>path starts with /api/ ?"}

    EDGE -->|"No"| SPA["🌐 Serve SPA<br>rewrite to /index.html"]
    SPA --> DONE(["✅ Response"])

    EDGE -->|"Yes"| FN["⚙️ FastAPI serverless function<br>api/index.py boots the app"]
    FN --> CORS["② CORS + security headers applied"]
    CORS --> ROUTE{"③ Route matches<br>/api/v1/* ?"}
    ROUTE -->|"No"| E404(["🚫 404 Not Found"])

    ROUTE -->|"Yes"| PUBLIC{"④ Public route?<br>login · refresh"}
    PUBLIC -->|"Yes"| HANDLER
    PUBLIC -->|"No"| AUTH{"⑤ Valid Bearer JWT?<br>get_current_user"}

    AUTH -->|"No / expired"| E401(["🔒 401 Unauthorized"])
    AUTH -->|"Yes"| ADMINQ{"⑥ Admin-only route?"}

    ADMINQ -->|"Yes"| ADMINCHK{"require_admin<br>role == admin ?"}
    ADMINCHK -->|"No"| E403(["⛔ 403 Forbidden"])
    ADMINCHK -->|"Yes"| HANDLER
    ADMINQ -->|"No"| HANDLER

    HANDLER["⑦ Route handler<br>Pydantic validates the request"] --> SVC["⑧ Service / CRUDBase<br>business logic"]
    SVC --> ORM["⑨ SQLAlchemy 2.0 session"]
    ORM --> NEON[("🗄️ Neon Postgres<br>pooled endpoint · TLS")]
    NEON --> AUDIT["⑩ Mutating call?<br>append to activity_log"]
    AUDIT --> RESP["⑪ Pydantic serializes the response"]
    RESP --> DONE

    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    classDef err fill:#b4563f,stroke:#7d3626,color:#ffffff
    classDef ok fill:#2f8f6b,stroke:#1c6349,color:#ffffff
    class EDGE,SPA edge
    class FN,CORS,HANDLER,SVC,ORM,RESP,AUDIT api
    class NEON db
    class E401,E403,E404 err
    class DONE ok
```

**Step by step:**

| # | Stage | What happens |
|:--:|---|---|
| ① | **Edge routing** | `vercel.json` rewrites `/api/(.*)` to the Python function; everything else falls through to `index.html` (SPA routing). |
| ② | **CORS + headers** | `CORS_ORIGINS` is enforced; CSP/HSTS/`X-Frame-Options` are set on the response. |
| ③ | **Route match** | All app routes live under `/api/v1`. Meta routes `GET /health` and `GET /` sit outside it. |
| ④ | **Public gate** | Only `POST /auth/login` and `POST /auth/refresh` skip authentication. |
| ⑤ | **Authentication** | `get_current_user` decodes the HS256 JWT with `SECRET_KEY`; missing/expired ⇒ **401**. |
| ⑥–⑦ | **Authorization** | Admin routes add `require_admin`; a non-admin gets **403**. |
| ⑧–⑨ | **Handler → ORM** | Pydantic validates input, the service layer runs the logic, SQLAlchemy 2.0 talks to Neon over the pooled endpoint. |
| ⑩ | **Audit** | Mutating actions append a row to `activity_log`. |
| ⑪ | **Serialize** | The response model shapes the JSON both clients decode against the shared contract. |

---

## 2 · Authentication sequence

A client trades credentials for a short-lived **access token** (~30 min) and a longer **refresh token** (~14 days). The access token rides on every subsequent request as `Authorization: Bearer <jwt>`. On iOS the tokens live in the **Keychain**; on web, in browser storage.

```mermaid
sequenceDiagram
    autonumber
    actor U as Recruiter
    participant C as Client<br>(web / iOS)
    participant API as FastAPI<br>/api/v1/auth
    participant DB as Neon<br>Postgres

    U->>C: Enter username + password
    C->>+API: POST /auth/login
    API->>+DB: Look up user
    DB-->>-API: User row (bcrypt hash, flags)

    alt Bad credentials
        API->>DB: Increment failed-login count
        API-->>C: 401 Unauthorized
    else Account locked / disabled
        API-->>C: 403 Forbidden
    else 2FA enabled, TOTP missing/wrong
        API-->>C: 401 (TOTP required)
    else Valid
        API->>API: Sign access + refresh JWT (HS256)
        API-->>-C: 200 {access_token, refresh_token}
        C->>C: Store tokens<br>Keychain (iOS) / browser (web)
    end

    Note over C,API: Every later request carries<br>Authorization: Bearer [access_token]

    C->>+API: GET /api/v1/dashboard/stats
    API->>API: get_current_user decodes JWT
    API->>+DB: Query
    DB-->>-API: Rows
    API-->>-C: 200 dashboard payload
```

> **Security notes.** Passwords are bcrypt-hashed with a lockout after `MAX_FAILED_LOGINS`, reuse blocked against the last `PASSWORD_HISTORY_SIZE` hashes, and an expiry policy (`PASSWORD_EXPIRY_DAYS`, admins exempt). TOTP 2FA secrets are **Fernet-encrypted at rest** with `ENCRYPTION_KEY` — the app fails closed if that key is unset.

---

## 3 · Transparent refresh on 401

Access tokens are deliberately short-lived. Rather than bounce a recruiter to the login screen mid-session, both clients catch the first **401**, silently exchange the refresh token for a fresh access token, and **replay the original request once**. The user never notices.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client interceptor<br>api.ts / APIClient
    participant API as FastAPI

    C->>+API: GET /recruits (expired access token)
    API-->>-C: 401 Unauthorized

    Note over C: First 401 → attempt refresh<br>(not a re-login)

    C->>+API: POST /auth/refresh (refresh token)
    alt Refresh token still valid
        API-->>-C: 200 {new access_token}
        C->>C: Persist new token
        C->>+API: Retry GET /recruits (new token)
        API-->>-C: 200 recruit list
    else Refresh token also expired
        API-->>C: 401 Unauthorized
        C->>C: Clear tokens → route to Login
    end
```

---

## 4 · The recruiting funnel (state machine)

A recruit isn't a mutable "status" field you overwrite. It's a **state machine backed by an append-only event log**. Every stage change writes an *immutable* `recruit_stage_event` row — so the funnel and trend analytics are **derived from history**, not from a single field that loses its past the moment it changes.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> lead: recruit created

    lead --> contacted: outreach made
    contacted --> applied: application in
    applied --> enrolled: joined the program
    enrolled --> commissioned: 🎖️ commissioned

    lead --> declined
    contacted --> declined
    applied --> declined
    enrolled --> declined

    commissioned --> [*]
    declined --> [*]

    note right of commissioned
        FUNNEL_ORDER climbs
        lead → contacted → applied
        → enrolled → commissioned
    end note
    note right of declined
        declined is tracked but
        excluded from FUNNEL_ORDER
    end note
```

**Why an event stream?** Because the questions the commander asks are historical: *How many leads did we convert last month? Where in the funnel do we leak? Which recruiter moved which recruit, and when?* Each `POST /recruits/{id}/stage` appends one event; `GET /analytics/funnel` counts the current position of each recruit, and `GET /analytics/trends` reconstructs transitions over a time window — all from the same immutable log.

```mermaid
flowchart LR
    A["POST /recruits/{id}/stage"] --> B["append immutable<br>recruit_stage_event"]
    B --> C[("🗄️ event log")]
    C --> D["GET /analytics/funnel<br>count per stage"]
    C --> E["GET /analytics/trends<br>transitions over time"]
    C --> F["GET /recruits/{id}/stage-history<br>full audit trail"]

    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    class A,B,D,E,F api
    class C db
```

---

## 5 · The CSV/Excel import pipeline

Recruiting lists arrive as spreadsheets. `POST /recruits/import` accepts a CSV or Excel upload, validates it **row by row**, and returns an `ImportResult` that reports exactly which rows failed and why — so a bad cell never silently drops a lead, and the good rows still land.

```mermaid
flowchart TD
    UP([📤 Upload CSV / XLSX]) --> PARSE["pandas reads the file"]
    PARSE --> LOOP{{"for each row"}}
    LOOP --> VAL{"Row valid?<br>required fields · enums · types"}
    VAL -->|"Yes"| INS["Create PotentialRecruit<br>+ baseline stage event"]
    VAL -->|"No"| ERR["Record row-level error<br>(row #, reason)"]
    INS --> NEXT{{"more rows?"}}
    ERR --> NEXT
    NEXT -->|"Yes"| LOOP
    NEXT -->|"No"| RESULT["📋 ImportResult<br>created count + per-row errors"]
    RESULT --> RESP(["200 — report back to the client"])

    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef ok fill:#2f8f6b,stroke:#1c6349,color:#ffffff
    classDef err fill:#b4563f,stroke:#7d3626,color:#ffffff
    class PARSE,INS,RESULT api
    class ERR err
    class RESP ok
```

---

<div align="center">
<sub>Next: the <a href="Backend-API">Backend API reference</a> · the <a href="Database">Database model</a> · or back to <a href="Architecture">Architecture</a>.</sub>
</div>
