<div align="center">

# 📱 Det 695 — iOS app

**A native SwiftUI client for the Det 695 recruiting backend.** It talks to the
same FastAPI service and OpenAPI contract as the web app
(`../shared/openapi.json`), so the two clients read as one product.

![Swift](https://img.shields.io/badge/Swift-F05138?style=flat-square&logo=swift&logoColor=white)
![SwiftUI](https://img.shields.io/badge/SwiftUI-0C1C33?style=flat-square&logo=apple&logoColor=white)
![Xcode](https://img.shields.io/badge/Xcode_15+-147EFB?style=flat-square&logo=xcode&logoColor=white)
![iOS](https://img.shields.io/badge/iOS_17+-000000?style=flat-square&logo=apple&logoColor=white)

</div>

```mermaid
flowchart LR
    LOGIN["🔐 Login<br>Keychain JWT"]
    SHELL["Tabbed shell"]
    DASH["📊 Dashboard<br>stats + funnel"]
    REC["🎯 Recruits"]
    CAD["🎓 Cadets"]
    API["⚙️ FastAPI<br>/api/v1"]

    LOGIN -->|token| SHELL
    SHELL --> DASH & REC & CAD
    DASH & REC & CAD -->|async URLSession| API

    classDef ios fill:#0c1c33,stroke:#050d1a,color:#ffffff
    classDef api fill:#2f9bd8,stroke:#1d6fa0,color:#ffffff
    classDef edge fill:#f2a83b,stroke:#c9852a,color:#3a2600
    class SHELL,DASH,REC,CAD ios
    class API api
    class LOGIN edge
```

## What's here

- **Login → tabbed shell** (Dashboard · Recruits · Cadets) with Keychain-backed
  JWT auth and transparent token refresh — the same contract as `web/src/lib/api.ts`.
- **Dashboard** — headline stat tiles + "The Ascent" funnel.
- **Recruits** — searchable list with a stage filter.
- **Cadets** — searchable directory with an active/inactive/graduated filter and
  status dots matching the web palette.

## Layout

```
ios/
  project.yml            XcodeGen spec (generates the .xcodeproj)
  Det695/
    Det695App.swift      @main entry
    Support/             Config (API base URL) + Keychain
    Networking/          APIClient (async URLSession) + APIError
    Models/              Codable types mirroring the OpenAPI schemas
    State/               Session (auth ObservableObject)
    Theme/               Brand palette mirrored from web tokens
    Views/               Root / Login / Dashboard / Recruits / Cadets
```

There is **no committed `.xcodeproj`** — it's generated from `project.yml` so
there's no fragile `pbxproj` to hand-merge.

## Build & run

Requires **Xcode 15+** (iOS 17 deployment target).

```bash
brew install xcodegen        # one-time
cd ios
xcodegen generate           # writes Det695.xcodeproj + Det695/Info.plist
open Det695.xcodeproj        # ⌘R to run in the simulator
```

### Point it at a backend

By default the app calls `http://localhost:8099/api/v1`, which the iOS Simulator
reaches on the Mac host. Start the backend first:

```bash
cd ../backend && uv run uvicorn app.main:app --port 8099
```

Log in with the demo admin: `admin` / `Det695Demo!`.

To target a different backend (e.g. a physical device on your LAN, or a deployed
URL), set the `DET695_API_BASE` environment variable in the Run scheme, e.g.
`http://192.168.1.20:8099/api/v1`. The `Info.plist` already allows insecure
`localhost` HTTP for local development; a deployed backend should be HTTPS.

## Notes

- Models decode with `.convertFromSnakeCase`, so Swift properties are camelCase
  while the JSON stays snake_case — no hand-written `CodingKeys`.
- `RecruitStage` decodes defensively (`.from(_:)` falls back to `.lead`) so an
  unexpected server value never crashes a list.
