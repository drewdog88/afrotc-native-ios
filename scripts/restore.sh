#!/usr/bin/env bash
#
# Restore a Neon backup (produced by .github/workflows/backup.yml) into a target
# database. Use this for a real recovery — see BACKUP.md for the full runbook.
#
# Usage:
#   TARGET_DATABASE_URL="postgresql://USER:PASS@ep-XXXX.us-east-1.aws.neon.tech/neondb?sslmode=require" \
#     scripts/restore.sh [BACKUP_TAG]
#
#   BACKUP_TAG  a backup release tag (e.g. backup-20260703-051945). Omit to use
#               the newest backup-* release.
#
# TARGET_DATABASE_URL MUST be the DIRECT (non-pooled) endpoint — pg_restore must
# not run through PgBouncer (no "-pooler" in the host).
#
# Requirements:
#   - gh, authenticated to github.com (gh auth status)   -> the backups repo
#   - pg_restore / psql >= 17  (macOS: brew install libpq && brew link --force libpq)
#
set -euo pipefail

REPO="drewdog88/afrotc-native-ios"
TAG="${1:-}"

: "${TARGET_DATABASE_URL:?Set TARGET_DATABASE_URL to the DIRECT (non-pooled) connection string of the restore target}"

# Safety: never restore through the pooler.
case "$TARGET_DATABASE_URL" in
  *-pooler*)
    echo "ERROR: TARGET_DATABASE_URL points at a '-pooler' host. Use the DIRECT endpoint (strip '-pooler')." >&2
    exit 1 ;;
esac

command -v pg_restore >/dev/null 2>&1 || {
  echo "ERROR: pg_restore not found. macOS: brew install libpq && brew link --force libpq" >&2
  exit 1; }

# pg_restore must be >= the Neon server major (17).
PGV="$(pg_restore --version | grep -oE '[0-9]+' | head -1)"
if [ "${PGV:-0}" -lt 17 ]; then
  echo "ERROR: pg_restore is v${PGV}; Neon server is 17. Install the v17 client." >&2
  exit 1
fi

# Resolve the tag to restore (newest backup-* if not given).
if [ -z "$TAG" ]; then
  TAG="$(gh release list --repo "$REPO" --limit 200 --json tagName,createdAt \
    --jq 'map(select(.tagName|startswith("backup-"))) | sort_by(.createdAt) | reverse | .[0].tagName')"
  [ -n "$TAG" ] || { echo "ERROR: no backup-* releases found in $REPO" >&2; exit 1; }
fi
echo ">> Backup to restore: $TAG"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
gh release download "$TAG" --repo "$REPO" --pattern '*.dump' --dir "$WORK"
DUMP="$(ls "$WORK"/*.dump)"
echo ">> Downloaded $(basename "$DUMP") ($(wc -c < "$DUMP" | tr -d ' ') bytes)"

# Prove it is a well-formed custom-format archive before touching the target.
pg_restore --list "$DUMP" >/dev/null || { echo "ERROR: not a valid pg_dump archive" >&2; exit 1; }

TARGET_HOST="$(printf '%s' "$TARGET_DATABASE_URL" | sed -E 's#^.*@##; s#[/?].*$##')"
echo ">> Target host: $TARGET_HOST"
read -r -p ">> This will WRITE data into the target (drops matching objects first). Continue? [y/N] " ans
[ "$ans" = "y" ] || { echo "Aborted."; exit 1; }

# --clean --if-exists lets this run against a non-empty target; harmless on a fresh one.
pg_restore --no-owner --no-privileges --clean --if-exists -d "$TARGET_DATABASE_URL" "$DUMP"

echo ">> Restore complete. Row counts:"
psql "$TARGET_DATABASE_URL" -c \
  "SELECT relname AS table, n_live_tup AS approx_rows FROM pg_stat_user_tables ORDER BY relname;" || true
echo ">> If promoting this DB: point Vercel DATABASE_URL at its POOLED url and redeploy."
