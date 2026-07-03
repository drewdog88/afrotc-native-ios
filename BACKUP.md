# Backup & Disaster Recovery

**The single source of truth is Neon Postgres.** There is no local/SQLite fallback
and no application-level backup job. The old Flask app's custom backup-to-blob
scheduler (`backup_to_blob.py`, `neon_backup_scheduler.py`) is **not** part of this
codebase — it is intentionally replaced by Neon's native durability features below.

## Recovery mechanisms (Neon-native)

1. **Point-in-Time Restore (PITR).** Neon continuously retains WAL history, so the
   database can be restored to any moment inside the retention window (bounded by the
   project's plan — verify the exact window in the Neon console under
   *Project → Settings → Storage*). Use this for "undo a bad migration / accidental
   `DELETE`" scenarios.

2. **Branching.** Create a branch from `main` at a past timestamp to inspect or
   recover data *without* disturbing production, then promote or copy rows back.
   This is the preferred way to investigate data loss before committing to a full
   restore. Branches are copy-on-write and cheap.

3. **Schema versioning.** The schema itself is reproducible from Alembic migrations
   in `backend/alembic/`. `alembic upgrade head` rebuilds the schema on any fresh
   Neon branch/project; `backend/scripts/seed_demo.py` reseeds reference data.

## Runbook

| Scenario | Action |
|---|---|
| Bad migration / bad bulk edit just shipped | Neon console → **Restore** to a timestamp just before the change (or branch at that time, verify, then restore). |
| Need to inspect old data safely | Create a Neon **branch** at the target timestamp; connect a throwaway `DATABASE_URL` to it. |
| Total project loss | New Neon project → set `DATABASE_URL` in Vercel → `alembic upgrade head` → reseed. |

## What is NOT backed up here

Uploaded materials (`backend/app/api/v1/materials.py`) live in Vercel Blob, which has
its own durability; they are outside the Postgres PITR window. If materials become
business-critical, add a periodic Blob export — not needed at current usage.

## Verify PITR retention

The retention window depends on the Neon plan. Confirm it in the Neon console and,
if the current window is shorter than desired, either upgrade the plan or accept the
documented window. As of this writing the recovery posture above is the intended
strategy; there is deliberately no cron/scheduler to maintain.
