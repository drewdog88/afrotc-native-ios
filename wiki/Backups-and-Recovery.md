# Backups & Recovery

**Neon Postgres is the single source of truth — there is no local/SQLite
fallback.** The authoritative runbook lives in [`BACKUP.md`](https://github.com/drewdog88/afrotc-native-ios/blob/main/BACKUP.md)
at the repo root; this page is the overview.

## Nightly backup: pg_dump → GitHub Release (free, plan-independent)

Neon's built-in point-in-time restore keeps only a short window on the free plan,
and long-retention/scheduled backups need a paid plan. So the real backup is
external:

- **`.github/workflows/backup.yml`** runs nightly (`0 9 * * *` UTC ≈ 02:00
  Pacific) and on demand (Actions → *DB Backup* → **Run workflow**).
- It `pg_dump`s the DB (`-Fc --no-owner --no-privileges`) using the
  `BACKUP_DATABASE_URL` secret — a **direct, non-pooled** Neon string (`pg_dump`
  must not run through PgBouncer).
- Each dump is published as a dated **pre-release** (`backup-YYYYMMDD-HHMMSS`)
  with the `.dump` attached. It keeps the newest **14** and prunes the rest
  (`KEEP` env). The job aborts if the dump is suspiciously small.

> Rotate the secret with
> `gh secret set BACKUP_DATABASE_URL --repo drewdog88/afrotc-native-ios`.

## Weekly restore drill (proves the backups actually restore)

A backup you've never restored is just a hope. **`.github/workflows/restore-drill.yml`**
verifies it automatically:

- Runs **Mondays** (`0 10 * * 1` UTC) and on demand (optional `tag` input; blank
  = newest).
- Restores the chosen backup into a **throwaway `postgres:17` container in CI** —
  never the live Neon DB, zero risk.
- Asserts all **11 expected tables** are present, writes a per-table row-count to
  the run Summary, and **fails loudly if `users` is empty** (a restore nobody
  could log into). On failure it opens/dedupes a `restore-drill-failure` issue.

Green summary = restorable. A red drill means the newest backup is suspect —
investigate before you need it.

## Restore for real (recovery)

Restore into a **fresh target**, verify, then promote. Full steps in `BACKUP.md`;
the helper is `scripts/restore.sh`:

```bash
TARGET_DATABASE_URL="postgresql://USER:PASS@ep-XXXX.neon.tech/neondb?sslmode=require" \
  scripts/restore.sh                     # newest backup
# or: scripts/restore.sh backup-YYYYMMDD-HHMMSS
```

It refuses a `-pooler` host and a pre-17 client, verifies the archive, prompts,
restores (`pg_restore --no-owner --no-privileges --clean --if-exists`), then
prints row counts. Prereqs: `gh` authenticated, `pg_restore`/`psql` **≥ 17**
(`brew install libpq && brew link --force libpq`).

To **promote** a restored DB to production: point Vercel's `DATABASE_URL` at the
restored DB's **pooled** URL and redeploy; keep DDL on the direct host.

## What's covered

- **Everything in Postgres — including uploaded documents.** Documents are stored
  as `bytea` (`recruitment_document.file_data`), so they're inside the dump. (The
  older note that materials live only in Vercel Blob is obsolete — the app serves
  documents from Postgres now.)
- **Schema is always reproducible** from Alembic (`alembic upgrade head`) on any
  fresh Neon branch/project; `seed_demo.py` reseeds reference data. A dump restore
  layers the data back on top.

## Secondary: Neon PITR + branching

For a *recent* mistake, Neon's own **point-in-time restore** and **branching**
(console) are faster than a full restore — within the free plan's retention
window. If that window is ever too short and a paid plan isn't an option, shorten
the backup cron (e.g. twice daily) instead.
