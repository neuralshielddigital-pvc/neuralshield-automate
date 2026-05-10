#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_FILE="${1:?Usage: restore_db.sh /path/to/backup.dump}"

pg_restore "$BACKUP_FILE" --dbname="$DATABASE_URL" --clean --if-exists --no-owner
echo "Database restored from: $BACKUP_FILE"
