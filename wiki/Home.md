<div align="center">

<img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/ios/Det695/Assets.xcassets/DetPatch.imageset/det695-patch.png" alt="AFROTC Detachment 695 patch" width="150" />

# AFROTC Detachment 695 — Recruiting Command Platform

### One product. Three surfaces. One source of truth.

**A modern recruiting & cadet-management platform for AFROTC Detachment 695** — University of Portland, covering the Pacific Northwest from Seattle to Portland to campuses across Oregon and Washington.

<br>

<a href="Architecture"><img src="https://img.shields.io/badge/%E2%96%B6%20Architecture-0c1c33?style=for-the-badge" alt="Architecture" /></a>
<a href="How-It-Works"><img src="https://img.shields.io/badge/%E2%9A%99%20How%20It%20Works-1e4c87?style=for-the-badge" alt="How It Works" /></a>
<a href="Backend-API"><img src="https://img.shields.io/badge/%7B%7D%20API%20Reference-2f9bd8?style=for-the-badge" alt="API Reference" /></a>
<a href="Roadmap"><img src="https://img.shields.io/badge/%E2%98%85%20Roadmap-f2a83b?style=for-the-badge&logoColor=black" alt="Roadmap" /></a>

<br><br>

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Neon](https://img.shields.io/badge/Neon_Postgres-00E599?style=for-the-badge&logo=neon&logoColor=black)
![React](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Swift](https://img.shields.io/badge/Swift-F05138?style=for-the-badge&logo=swift&logoColor=white)
![iOS](https://img.shields.io/badge/iOS_17-000000?style=for-the-badge&logo=apple&logoColor=white)
![OpenAPI](https://img.shields.io/badge/OpenAPI-6BA539?style=for-the-badge&logo=openapiinitiative&logoColor=white)
![JWT](https://img.shields.io/badge/JWT_Auth-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)

</div>

---

## Why this platform exists

> **Recruiting is a funnel, and funnels leak when the data is scattered.** Spreadsheets on one laptop, contacts in someone's phone, event notes on paper, "who's following up with that lead?" in a group chat. Det 695 runs on **one database, one API, and one contract** — so a recruiter on a phone at a high-school college fair, a cadre member at a desktop, and the analytics dashboard the commander reviews are all looking at *the same truth at the same instant.*

This is a real, deployed system — not a prototype. It ships to production on free-tier infrastructure, backs itself up every night, and **proves its own backups restore** every week.

<div align="center">

|  | What it delivers |
|:--:|:--|
| 🎯 | **Full recruiting funnel** — leads climb `lead → contacted → applied → enrolled → commissioned` with an *immutable, append-only* audit trail behind every stage change |
| 🗺️ | **Territory map** of geocoded Pacific-Northwest schools and contacts |
| 📊 | **Live analytics** — funnel conversion, trends, and a commander's dashboard fed from the event stream |
| 📱 | **Native iPhone app** *and* a browser app, built against the **same API contract** — never out of sync |
| 🔒 | **Real security** — JWT auth, bcrypt + password policy, Fernet-encrypted TOTP 2FA, hardened CSP |
| 💾 | **Disaster-ready** — nightly `pg_dump` backups and an automated weekly restore drill that fails loudly if a backup is bad |

</div>

## The shape of it — three surfaces, one truth

```mermaid
flowchart TB
    subgraph clients["🖥️  Client surfaces"]
        direction LR
        WEB["🌐 Web app<br>React 19 · TypeScript · Vite<br><i>cadre &amp; staff, day to day</i>"]
        IOS["📱 iOS app<br>SwiftUI · Keychain<br><i>recruiters in the field</i>"]
    end

    CONTRACT{{"📜 shared/openapi.json<br>the single API contract<br>both clients are generated from"}}

    subgraph cloud["☁️  Cloud — Vercel + Neon"]
        API["⚙️ Backend API<br>FastAPI · SQLAlchemy 2.0<br>/api/v1/* · OpenAPI at /docs"]
        DB[("🗄️ Neon Postgres<br>single source of truth<br>11 tables")]
    end

    WEB ==> CONTRACT
    IOS ==> CONTRACT
    CONTRACT ==> API
    API ==>|"postgresql+psycopg<br>pooled · TLS"| DB

    classDef web fill:#1e4c87,stroke:#16396a,color:#ffffff
    classDef ios fill:#0c1c33,stroke:#000000,color:#ffffff
    classDef api fill:#2f9bd8,stroke:#1c6fa0,color:#05243a
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    class WEB web
    class IOS ios
    class API api
    class DB db
    class CONTRACT edge
```

<div align="center"><sub><b>Change the API once and both front-ends change with it.</b> That is what keeps the web app and the phone reading as <i>one product</i> — not two apps that happen to share a logo.</sub></div>

## See it

<div align="center">

<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/02-dashboard.png" alt="Commander's dashboard" /><br><sub align="center"><b>Commander's dashboard</b> — headline stats + "The Ascent" funnel</sub></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-map.png" alt="Territory map" /><br><sub><b>Territory map</b> — geocoded PNW schools &amp; contacts</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/screen-pipeline.png" alt="Recruiting pipeline" /><br><sub><b>Pipeline</b> — the recruiting funnel, stage by stage</sub></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/drewdog88/afrotc-native-ios/main/web/shots/04-dashboard-dark.png" alt="Dark mode" /><br><sub><b>Command navy</b> — full dark mode</sub></td>
  </tr>
</table>

<sub>More screens on the <a href="Web-App">Web App</a> page.</sub>

</div>

## Start here

| Page | What you'll find |
|---|---|
| **[Architecture](Architecture)** | How the three surfaces fit together — the big picture |
| **[How It Works](How-It-Works)** | 🔬 The deep dive — request lifecycle, auth flow, the funnel state machine, import pipeline |
| **[Backend API](Backend-API)** | The FastAPI service — endpoints, auth, security, config |
| **[Web App](Web-App)** | The React/Vite client, its data flow, and the full screenshot gallery |
| **[iOS App](iOS-App)** | The SwiftUI client and how to build it |
| **[Database](Database)** | Neon Postgres — the entity model, migrations, seeding |
| **[Backups & Recovery](Backups-and-Recovery)** | Nightly dumps, the weekly restore drill, the recovery runbook |
| **[Deployment](Deployment)** | How web + API ship to Vercel |
| **[Development Process](Development-Process)** | Running all three surfaces locally |
| **[Testing](Testing)** | What's verified today, and the gaps |
| **[Roadmap](Roadmap)** | What's next |

## Ground rules

- **Neon Postgres is the only runtime datastore.** No local/SQLite fallback in deployed environments — see [Backups & Recovery](Backups-and-Recovery).
- **Data is real and regional.** Pacific-Northwest schools and contacts only; never seed fictitious out-of-region (e.g. California) data.
- **Secrets never land in the repo.** Connection strings and keys live in `.env` (gitignored) locally and in Vercel / GitHub Actions secrets in the cloud.

<div align="center"><br><sub>AFROTC Detachment 695 · University of Portland · Pacific Northwest</sub></div>
