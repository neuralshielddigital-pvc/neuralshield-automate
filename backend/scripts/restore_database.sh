#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
        pwd
)"

# shellcheck source=db_backup_common.sh
source "${SCRIPT_DIR}/db_backup_common.sh"

require_postgresql_tools
ensure_directories

BACKUP_FILE="${1:-}"
TARGET_DATABASE_URL="${TARGET_DATABASE_URL:-}"

[[ -n "$BACKUP_FILE" ]] ||
    fail "Usage: TARGET_DATABASE_URL='...' $0 /path/to/backup.dump"

[[ -f "$BACKUP_FILE" ]] ||
    fail "Backup file not found: ${BACKUP_FILE}"

[[ -s "$BACKUP_FILE" ]] ||
    fail "Backup file is empty: ${BACKUP_FILE}"

[[ -n "$TARGET_DATABASE_URL" ]] ||
    fail "TARGET_DATABASE_URL is required"

SOURCE_DATABASE_URL="$(read_database_url)"

if same_database_target \
    "$SOURCE_DATABASE_URL" \
    "$TARGET_DATABASE_URL"; then

    if [[ "${ALLOW_PRODUCTION_RESTORE:-no}" != "yes" ]]; then
        fail "Refusing restore into source/production database. Set ALLOW_PRODUCTION_RESTORE=yes only during an approved disaster-recovery operation."
    fi
fi

"${SCRIPT_DIR}/verify_backup.sh" "$BACKUP_FILE"

TARGET_DATABASE_NAME="$(
    database_url_field "$TARGET_DATABASE_URL" database
)"

TARGET_DATABASE_HOST="$(
    database_url_field "$TARGET_DATABASE_URL" host
)"

log "Restore target database: ${TARGET_DATABASE_NAME}"
log "Restore target host: ${TARGET_DATABASE_HOST}"
log "Validating target connection"

validate_database_connection "$TARGET_DATABASE_URL"

if [[ "${CONFIRM_RESTORE:-}" != "RESTORE" ]]; then
    fail "Set CONFIRM_RESTORE=RESTORE to confirm destructive target restore"
fi

log "Starting restore"

pg_restore \
    --dbname="$TARGET_DATABASE_URL" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    --verbose \
    "$BACKUP_FILE"

log "Restore completed"

psql "$TARGET_DATABASE_URL" \
    --set=ON_ERROR_STOP=1 \
    --no-psqlrc \
    --quiet \
    --tuples-only \
    --command="
        SELECT COUNT(*)
        FROM pg_catalog.pg_tables
        WHERE schemaname NOT IN (
            'pg_catalog',
            'information_schema'
        );
    "

log "Post-restore database query: PASS"
log "RESULT: PASSED"
