#!/usr/bin/env bash

set -u
set -o pipefail

BASE_DIR="/home/ubuntu/apps/automate"
BACKEND_DIR="$BASE_DIR/backend"
LOG_DIR="$BASE_DIR/monitoring/logs"
LOG_FILE="$LOG_DIR/health-check.log"

BACKEND_URL="https://api.neuralshielddigital.com/api/health"
FRONTEND_URL="https://app.neuralshielddigital.com"

DISK_THRESHOLD=80
MEMORY_THRESHOLD=85
SSL_THRESHOLD_DAYS=30
BACKUP_MAX_AGE_HOURS=26

BACKUP_DIR="$BACKEND_DIR/backups/database"

mkdir -p "$LOG_DIR"

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
    printf '%s %s\n' "$(timestamp)" "$*" | tee -a "$LOG_FILE"
}

failures=()

add_failure() {
    failures+=("$1")
    log "FAIL: $1"
}

log "Monitoring run started"

# Backend health
backend_response="$(curl -fsS --max-time 15 "$BACKEND_URL" 2>/dev/null || true)"

if [[ -z "$backend_response" ]]; then
    add_failure "Backend health endpoint is unreachable"
elif ! grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' <<<"$backend_response"; then
    add_failure "Backend health response does not report status=ok"
elif ! grep -q '"database"[[:space:]]*:[[:space:]]*"ok"' <<<"$backend_response"; then
    add_failure "Backend health response does not report database=ok"
else
    log "PASS: Backend API and database"
fi

# Frontend
frontend_code="$(
    curl -sS \
        -o /dev/null \
        -w '%{http_code}' \
        --max-time 15 \
        "$FRONTEND_URL" 2>/dev/null || true
)"

if [[ "$frontend_code" != "200" ]]; then
    add_failure "Frontend returned HTTP ${frontend_code:-unknown}"
else
    log "PASS: Frontend HTTP 200"
fi

# Backend systemd service
if systemctl is-active --quiet neuralshield-backend; then
    log "PASS: neuralshield-backend service active"
else
    add_failure "neuralshield-backend service is not active"
fi

# Nginx
if systemctl is-active --quiet nginx; then
    log "PASS: nginx service active"
else
    add_failure "nginx service is not active"
fi

# PM2 frontend
if command -v pm2 >/dev/null 2>&1; then
    pm2_json="$(pm2 jlist 2>/dev/null || true)"

    if grep -q '"status":"online"' <<<"$pm2_json"; then
        log "PASS: At least one PM2 process is online"
    else
        add_failure "No PM2 process is online"
    fi
else
    add_failure "pm2 command is unavailable"
fi

# Disk usage
disk_usage="$(
    df --output=pcent / \
    | tail -n 1 \
    | tr -dc '0-9'
)"

if [[ -z "$disk_usage" ]]; then
    add_failure "Unable to determine disk usage"
elif (( disk_usage >= DISK_THRESHOLD )); then
    add_failure "Disk usage is ${disk_usage}% (threshold ${DISK_THRESHOLD}%)"
else
    log "PASS: Disk usage ${disk_usage}%"
fi

# Memory usage based on MemAvailable
read -r mem_total mem_available < <(
    awk '
        /MemTotal:/ { total=$2 }
        /MemAvailable:/ { available=$2 }
        END { print total, available }
    ' /proc/meminfo
)

if [[ -z "${mem_total:-}" || -z "${mem_available:-}" || "$mem_total" -eq 0 ]]; then
    add_failure "Unable to determine memory usage"
else
    memory_usage=$(( (mem_total - mem_available) * 100 / mem_total ))

    if (( memory_usage >= MEMORY_THRESHOLD )); then
        add_failure "Memory usage is ${memory_usage}% (threshold ${MEMORY_THRESHOLD}%)"
    else
        log "PASS: Memory usage ${memory_usage}%"
    fi
fi

# Backup freshness
latest_backup="$(
    find "$BACKUP_DIR" \
        -maxdepth 1 \
        -type f \
        \( -name '*.dump' -o -name '*.sql.gz' -o -name '*.backup' \) \
        -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2-
)"

if [[ -z "$latest_backup" ]]; then
    add_failure "No database backup found in $BACKUP_DIR"
else
    backup_mtime="$(stat -c %Y "$latest_backup")"
    now_epoch="$(date +%s)"
    backup_age_hours=$(( (now_epoch - backup_mtime) / 3600 ))

    if (( backup_age_hours > BACKUP_MAX_AGE_HOURS )); then
        add_failure "Latest backup is ${backup_age_hours} hours old"
    else
        log "PASS: Latest backup is ${backup_age_hours} hours old"
    fi
fi

# SSL expiry
check_ssl() {
    local host="$1"
    local expiry
    local expiry_epoch
    local now_epoch
    local days_left

    expiry="$(
        echo \
        | openssl s_client \
            -connect "${host}:443" \
            -servername "$host" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null \
        | cut -d= -f2-
    )"

    if [[ -z "$expiry" ]]; then
        add_failure "Unable to read SSL certificate for $host"
        return
    fi

    expiry_epoch="$(date -d "$expiry" +%s 2>/dev/null || true)"
    now_epoch="$(date +%s)"

    if [[ -z "$expiry_epoch" ]]; then
        add_failure "Unable to parse SSL expiry for $host"
        return
    fi

    days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

    if (( days_left < SSL_THRESHOLD_DAYS )); then
        add_failure "SSL certificate for $host expires in ${days_left} days"
    else
        log "PASS: SSL certificate for $host has ${days_left} days remaining"
    fi
}

check_ssl "api.neuralshielddigital.com"
check_ssl "app.neuralshielddigital.com"

if (( ${#failures[@]} > 0 )); then
    log "Monitoring run completed with ${#failures[@]} failure(s)"
    printf '\nDetected failures:\n'

    for failure in "${failures[@]}"; do
        printf -- '- %s\n' "$failure"
    done

    exit 1
fi

log "Monitoring run completed successfully"
exit 0
