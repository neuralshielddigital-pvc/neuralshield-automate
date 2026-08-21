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

LOCK_FILE="${LOCK_DIR}/database-restore-drill.lock"
exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    fail "Another restore drill is already running"
fi

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

"${SCRIPT_DIR}/verify_backup.sh" "$BACKUP_FILE"

SOURCE_DATABASE_URL="$(read_database_url)"
SOURCE_DATABASE_NAME="$(
    database_url_field "$SOURCE_DATABASE_URL" database
)"

MAINTENANCE_DATABASE="${MAINTENANCE_DATABASE:-postgres}"
MAINTENANCE_URL="$(
    replace_database_in_url \
        "$SOURCE_DATABASE_URL" \
        "$MAINTENANCE_DATABASE"
)"

TIMESTAMP="$(date -u '+%Y%m%d%H%M%S')"
RANDOM_SUFFIX="$(
    python3 - <<'PY'
import secrets
print(secrets.token_hex(3))
PY
)"

TEMP_DATABASE_NAME="nsd_restore_${TIMESTAMP}_${RANDOM_SUFFIX}"
TEMP_DATABASE_URL="$(
    replace_database_in_url \
        "$SOURCE_DATABASE_URL" \
        "$TEMP_DATABASE_NAME"
)"

DATABASE_CREATED=0

cleanup() {
    if [[ "$DATABASE_CREATED" -eq 1 ]]; then
        log "Dropping temporary restore database: ${TEMP_DATABASE_NAME}"

        psql "$MAINTENANCE_URL" \
            --set=ON_ERROR_STOP=1 \
            --no-psqlrc \
            --quiet \
            --set=temp_database="$TEMP_DATABASE_NAME" <<'SQL' || true
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = :'temp_database'
  AND pid <> pg_backend_pid();

SELECT format(
    'DROP DATABASE IF EXISTS %I',
    :'temp_database'
)
\gexec
SQL
    fi
}

trap cleanup EXIT

log "Source database: ${SOURCE_DATABASE_NAME}"
log "Temporary restore database: ${TEMP_DATABASE_NAME}"
log "Creating temporary database"

psql "$MAINTENANCE_URL" \
    --set=ON_ERROR_STOP=1 \
    --no-psqlrc \
    --quiet \
    --set=temp_database="$TEMP_DATABASE_NAME" <<'SQL'
SELECT format(
    'CREATE DATABASE %I',
    :'temp_database'
)
\gexec
SQL

DATABASE_CREATED=1

log "Temporary database created"
log "Restoring backup into temporary database"

pg_restore \
    --dbname="$TEMP_DATABASE_URL" \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    --verbose \
    "$BACKUP_FILE"

log "Restore completed"

VALIDATION_OUTPUT="$(
    psql "$TEMP_DATABASE_URL" \
        --set=ON_ERROR_STOP=1 \
        --no-psqlrc \
        --quiet \
        --tuples-only \
        --field-separator='|' \
        --command="
            SELECT
                COUNT(*) FILTER (
                    WHERE schemaname NOT IN (
                        'pg_catalog',
                        'information_schema'
                    )
                ) AS user_tables,
                COUNT(*) FILTER (
                    WHERE schemaname = 'public'
                ) AS public_tables
            FROM pg_catalog.pg_tables;
        "
)"

USER_TABLE_COUNT="$(
    printf '%s\n' "$VALIDATION_OUTPUT" |
        awk -F'|' '{gsub(/[[:space:]]/, "", $1); print $1}'
)"

PUBLIC_TABLE_COUNT="$(
    printf '%s\n' "$VALIDATION_OUTPUT" |
        awk -F'|' '{gsub(/[[:space:]]/, "", $2); print $2}'
)"

[[ "$USER_TABLE_COUNT" =~ ^[0-9]+$ ]] ||
    fail "Could not validate restored table count"

[[ "$USER_TABLE_COUNT" -gt 0 ]] ||
    fail "Restore drill found zero user tables"

log "User tables restored: ${USER_TABLE_COUNT}"
log "Public tables restored: ${PUBLIC_TABLE_COUNT}"

ALEMBIC_TABLE_EXISTS="$(
    psql "$TEMP_DATABASE_URL" \
        --set=ON_ERROR_STOP=1 \
        --no-psqlrc \
        --quiet \
        --tuples-only \
        --command="
            SELECT CASE
                WHEN to_regclass('public.alembic_version') IS NULL
                THEN 'no'
                ELSE 'yes'
            END;
        " |
        tr -d '[:space:]'
)"

if [[ "$ALEMBIC_TABLE_EXISTS" == "yes" ]]; then
    ALEMBIC_VERSION="$(
        psql "$TEMP_DATABASE_URL" \
            --set=ON_ERROR_STOP=1 \
            --no-psqlrc \
            --quiet \
            --tuples-only \
            --command="
                SELECT version_num
                FROM public.alembic_version
                LIMIT 1;
            " |
            xargs
    )"

    log "Alembic version table: PASS"
    log "Alembic revision: ${ALEMBIC_VERSION:-unknown}"
else
    log "WARN: public.alembic_version was not found"
fi

log "Temporary restore validation: PASS"
log "RESULT: PASSED"

cleanup
DATABASE_CREATED=0
trap - EXIT
