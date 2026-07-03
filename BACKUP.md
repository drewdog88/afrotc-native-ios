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

### Restore from a backup

1. Download the `.dump` asset from the desired release
   (Releases tab, or `gh release download <tag>`).
2. Restore into a target database (a fresh Neon branch/project, or local scratch):
   ```
   pg_restore --no-owner --no-privileges -d "$TARGET_DATABASE_URL" det695-YYYYMMDD-HHMMSS.dump
   ```
3. Point `DATABASE_URL` (in Vercel) at the restored database if promoting it.

> The GitHub secret `BACKUP_DATABASE_URL` is the direct endpoint (the pooled
> `-pooler` host stripped) because `pg_dump` should not run through PgBouncer.
> Rotate it with `gh secret set BACKUP_DATABASE_URL --repo drewdog88/afrotc-native-ios`.

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
