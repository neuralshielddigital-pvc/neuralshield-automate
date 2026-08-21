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

if [[ -z "$BACKUP_FILE" ]]; then
    BACKUP_FILE="$(
        find "$BACKUP_ROOT" \
            -maxdepth 1 \
            -type f \
            -name '*.dump' \
            -printf '%T@ %p\n' |
            sort -nr |
            head -n 1 |
            cut -d' ' -f2-
    )"
fi

[[ -n "$BACKUP_FILE" ]] ||
    fail "No backup file found"

[[ -f "$BACKUP_FILE" ]] ||
    fail "Backup file does not exist: ${BACKUP_FILE}"

[[ -s "$BACKUP_FILE" ]] ||
    fail "Backup file is empty: ${BACKUP_FILE}"

CHECKSUM_FILE="${BACKUP_FILE}.sha256"

[[ -f "$CHECKSUM_FILE" ]] ||
    fail "Checksum file does not exist: ${CHECKSUM_FILE}"

log "Verifying backup: ${BACKUP_FILE}"

(
    cd "$(dirname "$BACKUP_FILE")"
    sha256sum --check "$(basename "$CHECKSUM_FILE")"
)

log "SHA-256 checksum: PASS"

ARCHIVE_LIST="$(
    mktemp
)"

cleanup() {
    rm -f "$ARCHIVE_LIST"
}

trap cleanup EXIT

pg_restore --list "$BACKUP_FILE" >"$ARCHIVE_LIST"

[[ -s "$ARCHIVE_LIST" ]] ||
    fail "Archive list is empty"

OBJECT_COUNT="$(
    grep -Ev '^[[:space:]]*(;|$)' "$ARCHIVE_LIST" |
        wc -l |
        tr -d '[:space:]'
)"

[[ "$OBJECT_COUNT" -gt 0 ]] ||
    fail "No restorable objects found in archive"

TABLE_COUNT="$(
    grep -Ec ' TABLE ' "$ARCHIVE_LIST" || true
)"

TABLE_DATA_COUNT="$(
    grep -Ec ' TABLE DATA ' "$ARCHIVE_LIST" || true
)"

SEQUENCE_COUNT="$(
    grep -Ec ' SEQUENCE ' "$ARCHIVE_LIST" || true
)"

BACKUP_SIZE_BYTES="$(
    stat --format='%s' "$BACKUP_FILE"
)"

log "Archive format validation: PASS"
log "Restorable objects: ${OBJECT_COUNT}"
log "Table definitions: ${TABLE_COUNT}"
log "Table-data entries: ${TABLE_DATA_COUNT}"
log "Sequence entries: ${SEQUENCE_COUNT}"
log "Backup size: ${BACKUP_SIZE_BYTES} bytes"
log "RESULT: PASSED"
