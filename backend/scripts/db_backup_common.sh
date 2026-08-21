#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

BACKEND_DIR="${BACKEND_DIR:-/home/ubuntu/apps/automate/backend}"
ENV_FILE="${ENV_FILE:-${BACKEND_DIR}/.env}"
BACKUP_ROOT="${BACKUP_ROOT:-${BACKEND_DIR}/backups/database}"
LOG_DIR="${LOG_DIR:-${BACKUP_ROOT}/logs}"
LOCK_DIR="${LOCK_DIR:-${BACKUP_ROOT}/locks}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

log() {
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
    log "ERROR: $*" >&2
    exit 1
}

require_command() {
    local command_name="$1"

    command -v "$command_name" >/dev/null 2>&1 ||
        fail "Required command not found: ${command_name}"
}

ensure_directories() {
    mkdir -p "$BACKUP_ROOT" "$LOG_DIR" "$LOCK_DIR"
    chmod 700 "$BACKUP_ROOT" "$LOG_DIR" "$LOCK_DIR"
}

read_database_url() {
    if [[ -n "${DATABASE_URL:-}" ]]; then
        printf '%s\n' "$DATABASE_URL"
        return 0
    fi

    [[ -f "$ENV_FILE" ]] ||
        fail "Environment file not found: ${ENV_FILE}"

    python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys

env_path = Path(sys.argv[1])

for raw_line in env_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()

    if not line or line.startswith("#"):
        continue

    if line.startswith("export "):
        line = line[len("export "):].lstrip()

    if not line.startswith("DATABASE_URL="):
        continue

    value = line.split("=", 1)[1].strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    if not value:
        raise SystemExit("DATABASE_URL is empty")

    print(value)
    break
else:
    raise SystemExit("DATABASE_URL not found")
PY
}

database_url_field() {
    local database_url="$1"
    local requested_field="$2"

    python3 - "$database_url" "$requested_field" <<'PY'
from urllib.parse import unquote, urlsplit
import sys

url = sys.argv[1]
field = sys.argv[2]
parsed = urlsplit(url)

values = {
    "scheme": parsed.scheme,
    "host": parsed.hostname or "",
    "port": str(parsed.port or 5432),
    "database": unquote(parsed.path.lstrip("/")),
    "username": unquote(parsed.username or ""),
}

if field not in values:
    raise SystemExit(f"Unsupported URL field: {field}")

print(values[field])
PY
}

replace_database_in_url() {
    local database_url="$1"
    local database_name="$2"

    python3 - "$database_url" "$database_name" <<'PY'
from urllib.parse import quote, urlsplit, urlunsplit
import sys

url = sys.argv[1]
database_name = sys.argv[2]
parsed = urlsplit(url)

new_path = "/" + quote(database_name, safe="")

print(
    urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            new_path,
            parsed.query,
            parsed.fragment,
        )
    )
)
PY
}

same_database_target() {
    local first_url="$1"
    local second_url="$2"

    python3 - "$first_url" "$second_url" <<'PY'
from urllib.parse import unquote, urlsplit
import sys

def identity(url: str) -> tuple[str, str, int, str]:
    parsed = urlsplit(url)
    return (
        (parsed.hostname or "").lower(),
        unquote(parsed.username or ""),
        parsed.port or 5432,
        unquote(parsed.path.lstrip("/")),
    )

raise SystemExit(0 if identity(sys.argv[1]) == identity(sys.argv[2]) else 1)
PY
}

require_postgresql_tools() {
    require_command python3
    require_command psql
    require_command pg_dump
    require_command pg_restore
    require_command sha256sum
    require_command flock
}

validate_database_connection() {
    local database_url="$1"

    psql "$database_url" \
        --set=ON_ERROR_STOP=1 \
        --no-psqlrc \
        --quiet \
        --tuples-only \
        --command="SELECT 1;" |
        grep -Eq '^[[:space:]]*1[[:space:]]*$' ||
        fail "Database connection validation failed"
}

safe_backup_basename() {
    local database_name="$1"
    local timestamp="$2"

    database_name="$(
        printf '%s' "$database_name" |
            tr -cs '[:alnum:]_.-' '_'
    )"

    printf '%s_%s' "$database_name" "$timestamp"
}
