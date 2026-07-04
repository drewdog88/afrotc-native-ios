<div align="center">

# 💾 Backups & Recovery

**A backup you've never restored is just a hope.** This platform proves its own backups restore — every week.

![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/pg__dump_17-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=flat-square&logo=neon&logoColor=black)

</div>

Neon Postgres is the single source of truth — there is no local/SQLite fallback. The authoritative runbook lives in [`BACKUP.md`](https://github.com/drewdog88/afrotc-native-ios/blob/main/BACKUP.md) at the repo root; this page is the overview.

## Nightly backup: pg_dump → GitHub Release

Neon's built-in point-in-time restore keeps only a short window on the free plan, and long-retention/scheduled backups need a paid plan. So the real backup is external and plan-independent.

```mermaid
flowchart LR
    CRON(["⏰ Nightly 0 9 * * * UTC<br>≈ 02:00 Pacific"]) --> DUMP["pg_dump -Fc<br>--no-owner --no-privileges"]
    DUMP -->|"BACKUP_DATABASE_URL<br>(direct, non-pooled)"| NEON[("🗄️ Neon")]
    DUMP --> SIZE{"dump big enough?"}
    SIZE -->|"No"| ABORT(["🚫 abort — too small"])
    SIZE -->|"Yes"| REL["📦 GitHub pre-release<br>backup-YYYYMMDD-HHMMSS.dump"]
    REL --> PRUNE["keep newest 14<br>prune the rest"]

    classDef ci fill:#2088FF,stroke:#0b5cbf,color:#ffffff
    classDef db fill:#00E599,stroke:#0c9b73,color:#04241f
    classDef err fill:#b4563f,stroke:#7d3626,color:#ffffff
    class CRON,DUMP,REL,PRUNE ci
    class NEON db
    class ABORT err
```

- **`.github/workflows/backup.yml`** runs nightly (`0 9 * * *` UTC ≈ 02:00 Pacific) and on demand (Actions → *DB Backup* → **Run workflow**).
- It `pg_dump`s the DB (`-Fc --no-owner --no-privileges`) using the `BACKUP_DATABASE_URL` secret — a **direct, non-pooled** Neon string (`pg_dump` must not run through PgBouncer).
- Each dump is published as a dated **pre-release** (`backup-YYYYMMDD-HHMMSS`) with the `.dump` attached. It keeps the newest **14** and prunes the rest (`KEEP` env). The job aborts if the dump is suspiciously small.

> Rotate the secret with `gh secret set BACKUP_DATABASE_URL --repo drewdog88/afrotc-native-ios`.

## Weekly restore drill (proves the backups actually restore)

**`.github/workflows/restore-drill.yml`** verifies restorability automatically — against a throwaway container, never the live DB.

```mermaid
flowchart TD
    START(["⏰ Mondays 0 10 * * 1 UTC<br>(or on demand)"]) --> PULL["fetch chosen backup<br>(blank = newest)"]
    PULL --> SPIN["🐳 spin up postgres:17<br>throwaway container"]
    SPIN --> RESTORE["pg_restore into container"]
    RESTORE --> CHECK{"all 11 tables present<br>AND users not empty?"}
    CHECK -->|"Yes"| GREEN(["✅ green — restorable<br>row counts in summary"])
    CHECK -->|"No"| RED(["❌ open/dedupe<br>restore-drill-failure issue"])

    classDef ci fill:#2088FF,stroke:#0b5cbf,color:#ffffff
    classDef ok fill:#2f8f6b,stroke:#1c6349,color:#ffffff
    classDef err fill:#b4563f,stroke:#7d3626,color:#ffffff
    class PULL,SPIN,RESTORE ci
    class GREEN ok
    class RED err
```

- Runs **Mondays** (`0 10 * * 1` UTC) and on demand (optional `tag` input; blank = newest).
- Restores the chosen backup into a **throwaway `postgres:17` container in CI** — never the live Neon DB, zero risk.
- Asserts all **11 expected tables** are present, writes a per-table row-count to the run Summary, and **fails loudly if `users` is empty** (a restore nobody could log into). On failure it opens/dedupes a `restore-drill-failure` issue.

Green summary = restorable. A red drill means the newest backup is suspect — investigate before you need it.

## Restore for real (recovery)

Restore into a **fresh target**, verify, then promote. Full steps in `BACKUP.md`; the helper is `scripts/restore.sh`:

```bash
TARGET_DATABASE_URL="postgresql://USER:PASS@ep-XXXX.neon.tech/neondb?sslmode=require" \
  scripts/restore.sh                     # newest backup
# or: scripts/restore.sh backup-YYYYMMDD-HHMMSS
```

It refuses a `-pooler` host and a pre-17 client, verifies the archive, prompts, restores (`pg_restore --no-owner --no-privileges --clean --if-exists`), then prints row counts. Prereqs: `gh` authenticated, `pg_restore`/`psql` **≥ 17** (`brew install libpq && brew link --force libpq`).

To **promote** a restored DB to production: point Vercel's `DATABASE_URL` at the restored DB's **pooled** URL and redeploy; keep DDL on the direct host.

## What's covered

- **Everything in Postgres — including uploaded documents.** Documents are stored as `bytea` (`recruitment_document.file_data`), so they're inside the dump. There is no external blob store to back up separately.
- **Schema is always reproducible** from Alembic (`alembic upgrade head`) on any fresh Neon branch/project; `seed_demo.py` reseeds reference data. A dump restore layers the data back on top.

## Secondary: Neon PITR + branching

For a *recent* mistake, Neon's own **point-in-time restore** and **branching** (console) are faster than a full restore — within the free plan's retention window. If that window is ever too short and a paid plan isn't an option, shorten the backup cron (e.g. twice daily) instead.
