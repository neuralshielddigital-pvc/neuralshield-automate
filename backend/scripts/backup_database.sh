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

LOCK_FILE="${LOCK_DIR}/database-backup.lock"
exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    fail "Another database backup is already running"
fi

TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
LOG_FILE="${LOG_DIR}/backup-${TIMESTAMP}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

DATABASE_URL_VALUE="$(read_database_url)"
DATABASE_NAME="$(
    database_url_field "$DATABASE_URL_VALUE" database
)"
DATABASE_HOST="$(
    database_url_field "$DATABASE_URL_VALUE" host
)"
DATABASE_PORT="$(
    database_url_field "$DATABASE_URL_VALUE" port
)"
DATABASE_USER="$(
    database_url_field "$DATABASE_URL_VALUE" username
)"

[[ -n "$DATABASE_NAME" ]] ||
    fail "Database name could not be parsed"

BACKUP_BASENAME="$(
    safe_backup_basename "$DATABASE_NAME" "$TIMESTAMP"
)"

TEMP_DUMP="${BACKUP_ROOT}/.${BACKUP_BASENAME}.dump.partial"
FINAL_DUMP="${BACKUP_ROOT}/${BACKUP_BASENAME}.dump"
TEMP_CHECKSUM="${BACKUP_ROOT}/.${BACKUP_BASENAME}.dump.sha256.partial"
FINAL_CHECKSUM="${FINAL_DUMP}.sha256"
TEMP_METADATA="${BACKUP_ROOT}/.${BACKUP_BASENAME}.metadata.txt.partial"
FINAL_METADATA="${BACKUP_ROOT}/${BACKUP_BASENAME}.metadata.txt"

cleanup() {
    rm -f "$TEMP_DUMP" "$TEMP_CHECKSUM" "$TEMP_METADATA"
}

trap cleanup EXIT

log "Starting PostgreSQL backup"
log "Database: ${DATABASE_NAME}"
log "Host: ${DATABASE_HOST}:${DATABASE_PORT}"
log "User: ${DATABASE_USER}"
log "Destination: ${FINAL_DUMP}"

validate_database_connection "$DATABASE_URL_VALUE"
log "Database connection: PASS"

pg_dump "$DATABASE_URL_VALUE" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --verbose \
    --file="$TEMP_DUMP"

[[ -s "$TEMP_DUMP" ]] ||
    fail "pg_dump created an empty backup file"

chmod 600 "$TEMP_DUMP"

pg_restore --list "$TEMP_DUMP" >/dev/null
log "Archive structure verification: PASS"

DUMP_SIZE_BYTES="$(
    stat --format='%s' "$TEMP_DUMP"
)"

[[ "$DUMP_SIZE_BYTES" -gt 0 ]] ||
    fail "Backup size validation failed"

(
    cd "$BACKUP_ROOT"
    sha256sum "$(basename "$TEMP_DUMP")"
) |
    sed "s/$(basename "$TEMP_DUMP")/$(basename "$FINAL_DUMP")/" \
        >"$TEMP_CHECKSUM"

chmod 600 "$TEMP_CHECKSUM"

cat >"$TEMP_METADATA" <<EOF
created_at_utc=${TIMESTAMP}
database=${DATABASE_NAME}
host=${DATABASE_HOST}
port=${DATABASE_PORT}
username=${DATABASE_USER}
format=PostgreSQL custom archive
compression=9
size_bytes=${DUMP_SIZE_BYTES}
pg_dump_version=$(pg_dump --version)
pg_restore_version=$(pg_restore --version)
retention_days=${RETENTION_DAYS}
EOF

chmod 600 "$TEMP_METADATA"

mv "$TEMP_DUMP" "$FINAL_DUMP"
mv "$TEMP_CHECKSUM" "$FINAL_CHECKSUM"
mv "$TEMP_METADATA" "$FINAL_METADATA"

trap - EXIT

log "Backup created successfully"
log "Backup file: ${FINAL_DUMP}"
log "Checksum file: ${FINAL_CHECKSUM}"
log "Metadata file: ${FINAL_METADATA}"
log "Backup size: ${DUMP_SIZE_BYTES} bytes"

log "Removing backup sets older than ${RETENTION_DAYS} days"

find "$BACKUP_ROOT" \
    -maxdepth 1 \
    -type f \
    \( \
        -name '*.dump' \
        -o -name '*.dump.sha256' \
        -o -name '*.metadata.txt' \
    \) \
    -mtime "+${RETENTION_DAYS}" \
    -print \
    -delete

find "$LOG_DIR" \
    -maxdepth 1 \
    -type f \
    -name 'backup-*.log' \
    -mtime "+${RETENTION_DAYS}" \
    -print \
    -delete

log "Retention cleanup completed"
log "RESULT: PASSED"
