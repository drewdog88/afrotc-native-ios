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
# Backups are age-ENCRYPTED (*.dump.age). You need the private age key to decrypt:
# point AGE_IDENTITY_FILE at your key file (default: ~/.config/det695/backup-age.key),
# or export AGE_KEY with its contents. This is the key you saved during one-time
# setup (also stored in the BACKUP_AGE_KEY GitHub secret). See BACKUP.md.
#
# Requirements:
#   - gh, authenticated to github.com (gh auth status)   -> the backups repo
#   - pg_restore / psql >= 17  (macOS: brew install libpq && brew link --force libpq)
#   - age  (macOS: brew install age)
#
set -euo pipefail

REPO="drewdog88/afrotc-native-ios"
TAG="${1:-}"
AGE_IDENTITY_FILE="${AGE_IDENTITY_FILE:-$HOME/.config/det695/backup-age.key}"

: "${TARGET_DATABASE_URL:?Set TARGET_DATABASE_URL to the DIRECT (non-pooled) connection string of the restore target}"

# Resolve the age identity: an explicit key file, or AGE_KEY contents written to a temp file.
command -v age >/dev/null 2>&1 || {
  echo "ERROR: age not found. macOS: brew install age" >&2; exit 1; }
KEYFILE=""
if [ -n "${AGE_KEY:-}" ]; then
  KEYFILE="$(mktemp)"; ( umask 077; printf '%s\n' "$AGE_KEY" > "$KEYFILE" )
elif [ -f "$AGE_IDENTITY_FILE" ]; then
  KEYFILE="$AGE_IDENTITY_FILE"
else
  echo "ERROR: no age key. Set AGE_IDENTITY_FILE to your key file, or export AGE_KEY." >&2
  echo "       (This is the private key from one-time setup / the BACKUP_AGE_KEY secret.)" >&2
  exit 1
fi

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
# Clean up the workdir and (if we minted one) the temp key on exit.
cleanup() { rm -rf "$WORK"; [ -n "${AGE_KEY:-}" ] && rm -f "$KEYFILE"; }
trap cleanup EXIT
gh release download "$TAG" --repo "$REPO" --pattern '*.dump.age' --dir "$WORK"
ENC="$(ls "$WORK"/*.dump.age)"
echo ">> Downloaded $(basename "$ENC") ($(wc -c < "$ENC" | tr -d ' ') bytes, encrypted)"

# Decrypt with the age identity before touching the target.
DUMP="${ENC%.age}"
age -d -i "$KEYFILE" -o "$DUMP" "$ENC" || {
  echo "ERROR: age decryption failed — wrong key for this backup?" >&2; exit 1; }
echo ">> Decrypted to $(basename "$DUMP") ($(wc -c < "$DUMP" | tr -d ' ') bytes)"

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
