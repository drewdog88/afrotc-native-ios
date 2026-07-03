# Backup & Disaster Recovery

**The single source of truth is Neon Postgres.** There is no local/SQLite fallback.

> ⚠️ **This repo is PUBLIC**, so GitHub Release assets are downloadable by anyone.
> Backups are therefore **age-encrypted** before upload — a Release asset is useless
> without the private key. Never publish a plaintext `.dump` here.

## One-time setup (encryption keys)

Backups are encrypted with [age](https://age-encryption.org) to a keypair you own.
Do this once (macOS: `brew install age gh`):

```bash
# 1. Generate the keypair. This prints the PUBLIC recipient ("age1...") and writes
#    the PRIVATE identity ("AGE-SECRET-KEY-1...") to the key file.
mkdir -p ~/.config/det695
age-keygen -o ~/.config/det695/backup-age.key       # note the "Public key: age1..." it prints

# 2. SAVE A COPY of ~/.config/det695/backup-age.key in your password manager.
#    If this key is ever lost, EVERY encrypted backup becomes unrecoverable.

# 3. Give GitHub the keys:
#    - PUBLIC key as a repo VARIABLE (used to encrypt; not sensitive):
gh variable set AGE_PUBLIC_KEY --repo drewdog88/afrotc-native-ios --body "age1........."
#    - PRIVATE key as a repo SECRET (used by the restore drill to decrypt):
gh secret set BACKUP_AGE_KEY --repo drewdog88/afrotc-native-ios < ~/.config/det695/backup-age.key
```

Until `AGE_PUBLIC_KEY` is set, the nightly backup **fails on purpose** rather than
upload an unencrypted dump. After setting it, trigger a run (Actions tab → *DB
Backup* → **Run workflow**) and confirm a new `backup-*` pre-release appears with a
`.dump.age` asset, then let the Monday restore-drill (or run it on demand) prove it
decrypts + restores.

## Primary backup: nightly encrypted pg_dump → GitHub Release (free)

Neon's built-in point-in-time restore keeps only a short history window on the free
plan, and scheduled/long-retention backups require a **paid** Neon plan. So the real
backup here is external and plan-independent:

- **`.github/workflows/backup.yml`** runs nightly (`0 9 * * *` UTC ≈ 02:00 Pacific),
  and can be run on demand from the Actions tab (**Run workflow**).
- It `pg_dump`s the database (custom format, `-Fc`, `--no-owner --no-privileges`)
  using the `BACKUP_DATABASE_URL` GitHub Actions secret — a **direct, non-pooled**
  Neon connection string (`sslmode=require`) — then **age-encrypts** the dump to the
  `AGE_PUBLIC_KEY` recipient. The plaintext never leaves the runner.
- Each encrypted dump is published as a **dated pre-release** (`backup-YYYYMMDD-HHMMSS`)
  with the **`.dump.age`** file attached. The workflow keeps the newest **14** and
  prunes older ones (adjust via the `KEEP` env in the workflow).

> The GitHub secret `BACKUP_DATABASE_URL` is the direct endpoint (the pooled
> `-pooler` host stripped) because `pg_dump` should not run through PgBouncer.
> Rotate it with `gh secret set BACKUP_DATABASE_URL --repo drewdog88/afrotc-native-ios`.

## Are the backups actually restorable? (routine integrity check)

A backup you have never restored is only a hope. **`.github/workflows/restore-drill.yml`**
proves it, automatically:

- Runs **every Monday** (`0 10 * * 1` UTC) and on demand (Actions tab → *Restore
  Drill* → **Run workflow**, optional `tag` to test a specific backup; blank = newest).
- Downloads the backup, **decrypts it** with the `BACKUP_AGE_KEY` secret, restores it
  into a **throwaway PostgreSQL 17 container in
  CI** (never the live Neon DB — zero risk), and asserts every expected table is
  present with its row count, failing loudly if `users` is empty (which would mean
  a restored DB nobody could log into).
- The run's **Summary** shows a table-by-table row count. Green = restorable.

If a drill ever goes red, the newest backup is suspect — investigate before you
need it.

## Restore for real — the easy way (one click, in the browser)

**`.github/workflows/restore.yml`** does a full recovery with no laptop and no crypto
by hand: Actions tab → *Restore backup to new Neon branch* → **Run workflow**, pick a
backup tag (blank = newest), Run. It creates a **fresh Neon branch**, decrypts the
backup with `BACKUP_AGE_KEY`, restores into that branch, and prints per-table row
counts in the run **Summary**. It **never touches your live database** — the data
lands in a new branch.

If the summary looks right, **promote** it: in the Neon console open that branch,
copy its **POOLED** connection string, set Vercel's `DATABASE_URL` to it (driver
`postgresql+psycopg://`, `-pooler` host, `?sslmode=require`), and redeploy. Delete
the branch when you're done. If it looks wrong, just delete the branch — nothing
live was changed.

> Needs the `NEON_API` secret (already set). If you have more than one Neon project,
> also set a `NEON_PROJECT_ID` repo variable so it knows which one; with a single
> project it auto-detects.

## Restore for real — by hand (recovery runbook)

Prefer the one-click workflow above. Use these steps if you'd rather drive it from
your Mac. You restore into a **fresh target**, verify, then promote it.

**Prerequisites:** `gh` authenticated to github.com; `pg_restore`/`psql` **≥ 17**
(macOS: `brew install libpq && brew link --force libpq`); `age` (macOS: `brew install age`)
and your private key at `~/.config/det695/backup-age.key` (from one-time setup).

1. **Create a fresh restore target** in Neon — a new **branch** of the project, or
   a new project. Copy its **DIRECT** (non-pooled, no `-pooler`) connection string.
2. **Restore** — the helper script downloads the encrypted backup, decrypts it, and
   restores it:
   ```
   TARGET_DATABASE_URL="postgresql://USER:PASS@ep-XXXX.us-east-1.aws.neon.tech/neondb?sslmode=require" \
     scripts/restore.sh            # newest backup; or: scripts/restore.sh backup-YYYYMMDD-HHMMSS
   ```
   It refuses a `-pooler` host and an old client, decrypts with your age key
   (`AGE_IDENTITY_FILE`, default `~/.config/det695/backup-age.key`, or `AGE_KEY`),
   verifies the archive, prompts before writing, then prints row counts. (Equivalent
   by hand: `age -d -i ~/.config/det695/backup-age.key det695-*.dump.age > det695.dump`
   then `pg_restore --no-owner --no-privileges --clean --if-exists -d "$TARGET_DATABASE_URL" det695.dump`.)
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

## Uploaded materials are covered too

Uploaded documents (`backend/app/api/v1/materials.py`) are stored as Postgres
`bytea` (`recruitment_document.file_data`) under the default `postgres` storage
backend, so they are **included in the `pg_dump`** and restored with everything
else. (A `vercel_blob` backend is stubbed but not implemented; if it's ever
enabled, blob objects would live outside the dump and would need their own export.)
