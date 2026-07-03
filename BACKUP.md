# Backup & Disaster Recovery

**The single source of truth is Neon Postgres.** There is no local/SQLite fallback.

## Primary backup: nightly pg_dump → GitHub Release (free)

Neon's built-in point-in-time restore keeps only a short history window on the free
plan, and scheduled/long-retention backups require a **paid** Neon plan. So the real
backup here is external and plan-independent:

- **`.github/workflows/backup.yml`** runs nightly (`0 9 * * *` UTC ≈ 02:00 Pacific),
  and can be run on demand from the Actions tab (**Run workflow**).
- It `pg_dump`s the database (custom format, `-Fc`, `--no-owner --no-privileges`)
  using the `BACKUP_DATABASE_URL` GitHub Actions secret — a **direct, non-pooled**
  Neon connection string (`sslmode=require`).
- Each dump is published as a **dated pre-release** (`backup-YYYYMMDD-HHMMSS`) with
  the `.dump` file attached. The workflow keeps the newest **14** and prunes older
  ones (adjust via the `KEEP` env in the workflow).

> The GitHub secret `BACKUP_DATABASE_URL` is the direct endpoint (the pooled
> `-pooler` host stripped) because `pg_dump` should not run through PgBouncer.
> Rotate it with `gh secret set BACKUP_DATABASE_URL --repo drewdog88/afrotc-native-ios`.

## Are the backups actually restorable? (routine integrity check)

A backup you have never restored is only a hope. **`.github/workflows/restore-drill.yml`**
proves it, automatically:

- Runs **every Monday** (`0 10 * * 1` UTC) and on demand (Actions tab → *Restore
  Drill* → **Run workflow**, optional `tag` to test a specific backup; blank = newest).
- Downloads the backup, restores it into a **throwaway PostgreSQL 17 container in
  CI** (never the live Neon DB — zero risk), and asserts every expected table is
  present with its row count, failing loudly if `users` is empty (which would mean
  a restored DB nobody could log into).
- The run's **Summary** shows a table-by-table row count. Green = restorable.

If a drill ever goes red, the newest backup is suspect — investigate before you
need it.

## Restore for real (recovery runbook)

Use this when you actually need the data back (corruption, bad migration, dropped
rows). You restore into a **fresh target**, verify, then promote it.

**Prerequisites:** `gh` authenticated to github.com; `pg_restore`/`psql` **≥ 17**
(macOS: `brew install libpq && brew link --force libpq`).

1. **Create a fresh restore target** in Neon — a new **branch** of the project, or
   a new project. Copy its **DIRECT** (non-pooled, no `-pooler`) connection string.
2. **Restore** — the helper script downloads the chosen backup and restores it:
   ```
   TARGET_DATABASE_URL="postgresql://USER:PASS@ep-XXXX.us-east-1.aws.neon.tech/neondb?sslmode=require" \
     scripts/restore.sh            # newest backup; or: scripts/restore.sh backup-YYYYMMDD-HHMMSS
   ```
   It refuses a `-pooler` host and an old client, verifies the archive, prompts
   before writing, then prints row counts. (Equivalent by hand:
   `pg_restore --no-owner --no-privileges --clean --if-exists -d "$TARGET_DATABASE_URL" det695-*.dump`.)
3. **Verify** the target: expected row counts, and `admin` login works against it.
4. **Promote** (only if replacing production): set Vercel `DATABASE_URL` to the
   restored DB's **POOLED** url (`...-pooler...?sslmode=require`, driver
   `postgresql+psycopg://`) — `vercel env rm DATABASE_URL production` then
   `vercel env add DATABASE_URL production` — and redeploy. Keep DDL/migrations on
   the direct (unpooled) host.

## Secondary: Neon PITR + branching (short window on free plan)

For a *recent* mistake (bad migration, accidental bulk edit), Neon's own tools are
faster than a restore — within the free plan's retention window:

- **Point-in-Time Restore** to a timestamp just before the change
  (Neon console → *Restore*). Retention window is bounded by the plan; confirm the
  current window under *Project → Settings → Storage*.
- **Branching**: branch from a past timestamp to inspect/recover data without
  touching production, then copy rows back or promote.

If the retention window is ever too short for comfort and a paid plan isn't an
option, shorten the backup cron interval (e.g. twice daily) instead.

## Schema is always reproducible

The schema is rebuilt from Alembic migrations in `backend/alembic/`
(`alembic upgrade head`) on any fresh Neon branch/project; `backend/scripts/seed_demo.py`
reseeds reference data. A dump restore brings back the data on top of that.

## Not covered by the DB dump

Uploaded materials (`backend/app/api/v1/materials.py`) live in Vercel Blob, which has
its own durability and is outside the Postgres dump. If materials become
business-critical, add a periodic Blob export — not needed at current usage.
