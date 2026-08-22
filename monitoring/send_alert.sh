#!/usr/bin/env bash

set -euo pipefail

BASE="/home/ubuntu/apps/automate/monitoring"

source "$BASE/monitoring.env"

SUBJECT="$1"

BODY_FILE="$2"

curl --silent --show-error \
    --url "smtp://${SMTP_HOST}:${SMTP_PORT}" \
    --ssl-reqd \
    --mail-from "$SMTP_USERNAME" \
    --mail-rcpt "$ALERT_TO" \
    --user "${SMTP_USERNAME}:${SMTP_PASSWORD}" \
    -T <(
cat <<EOF
From: ${ALERT_FROM}
To: ${ALERT_TO}
Subject: ${SUBJECT}
Content-Type: text/plain; charset=UTF-8

$(cat "$BODY_FILE")
EOF
)
