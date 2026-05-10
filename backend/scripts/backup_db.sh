#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/neuralshielddigital}"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"
mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
output="$BACKUP_DIR/neuralshielddigital_$timestamp.dump"

pg_dump "$DATABASE_URL" --format=custom --file="$output"
echo "Backup created: $output"
