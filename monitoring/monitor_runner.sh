#!/usr/bin/env bash

set -u
set -o pipefail

BASE_DIR="/home/ubuntu/apps/automate/monitoring"
HEALTH_CHECK="$BASE_DIR/health_check.sh"
SEND_ALERT="$BASE_DIR/send_alert.sh"

STATE_DIR="$BASE_DIR/state"
LOG_DIR="$BASE_DIR/logs"

STATE_FILE="$STATE_DIR/current-status"
LOCK_FILE="$STATE_DIR/monitor.lock"
ALERT_HISTORY="$LOG_DIR/alert-history.log"

mkdir -p "$STATE_DIR" "$LOG_DIR"

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

history_log() {
    printf '%s %s\n' "$(timestamp)" "$*" >> "$ALERT_HISTORY"
}

write_state() {
    local new_state="$1"
    local temporary_state

    temporary_state="$(mktemp "$STATE_DIR/status.XXXXXX")"
    printf '%s\n' "$new_state" > "$temporary_state"
    chmod 600 "$temporary_state"
    mv "$temporary_state" "$STATE_FILE"
}

previous_state="unknown"

if [[ -f "$STATE_FILE" ]]; then
    previous_state="$(cat "$STATE_FILE" 2>/dev/null || printf 'unknown')"
fi

# Prevent overlapping runs.
exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    history_log "SKIPPED: Another monitoring run is already active"
    exit 0
fi

output_file="$(mktemp)"
body_file="$(mktemp)"

cleanup() {
    rm -f "$output_file" "$body_file"
}

trap cleanup EXIT

case "${1:-}" in
    --simulate-failure)
        {
            echo "SIMULATED FAILURE"
            echo "This is a controlled monitoring alert test."
        } > "$output_file"
        result=1
        ;;

    --simulate-success)
        {
            echo "SIMULATED SUCCESS"
            echo "This is a controlled monitoring recovery test."
        } > "$output_file"
        result=0
        ;;

    "")
        if "$HEALTH_CHECK" > "$output_file" 2>&1; then
            result=0
        else
            result=$?
        fi
        ;;

    *)
        echo "Usage: $0 [--simulate-failure|--simulate-success]" >&2
        exit 2
        ;;
esac

# Preserve normal monitoring output in systemd journal.
cat "$output_file"

if (( result != 0 )); then
    if [[ "$previous_state" != "failed" ]]; then
        {
            echo "NeuralShieldDigital production monitoring detected a failure."
            echo
            echo "Host: $(hostname)"
            echo "Time (UTC): $(timestamp)"
            echo "Previous state: $previous_state"
            echo
            echo "Monitoring output:"
            echo "--------------------------------------------------"
            cat "$output_file"
        } > "$body_file"

        if "$SEND_ALERT" \
            "[CRITICAL] NeuralShieldDigital Production Alert" \
            "$body_file"
        then
            history_log "ALERT SENT: Production monitoring entered failed state"
        else
            history_log "ALERT ERROR: Failed to send production failure email"
        fi
    else
        history_log "ALERT SUPPRESSED: Failure is already active"
    fi

    write_state "failed"
    exit "$result"
fi

if [[ "$previous_state" == "failed" ]]; then
    {
        echo "NeuralShieldDigital production monitoring has recovered."
        echo
        echo "Host: $(hostname)"
        echo "Time (UTC): $(timestamp)"
        echo "Previous state: failed"
        echo "Current state: healthy"
        echo
        echo "Monitoring output:"
        echo "--------------------------------------------------"
        cat "$output_file"
    } > "$body_file"

    if "$SEND_ALERT" \
        "[RECOVERED] NeuralShieldDigital Production Monitoring" \
        "$body_file"
    then
        history_log "RECOVERY SENT: Production monitoring returned to healthy state"
    else
        history_log "RECOVERY ERROR: Failed to send recovery email"
    fi
fi

write_state "healthy"
history_log "HEALTHY: Monitoring run completed successfully"

exit 0
