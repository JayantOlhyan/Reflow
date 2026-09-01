#!/usr/bin/env bash
# ==============================================================================
# Reflow — Database & Media Storage Backup Script
# ==============================================================================
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./storage/backups}"
mkdir -p "${BACKUP_DIR}"

DB_BACKUP="${BACKUP_DIR}/reflow_db_${TIMESTAMP}.sql"
MEDIA_BACKUP="${BACKUP_DIR}/reflow_media_${TIMESTAMP}.tar.gz"

echo "=== Reflow Backup Starting [${TIMESTAMP}] ==="

# PostgreSQL Dump
if command -v docker >/dev/null 2>&1 && docker ps | grep -q reflow_postgres; then
  echo "--> Performing PostgreSQL dump from reflow_postgres container..."
  docker exec -t reflow_postgres pg_dump -U reflow -d reflow > "${DB_BACKUP}"
elif command -v pg_dump >/dev/null 2>&1; then
  echo "--> Performing local pg_dump..."
  pg_dump -U reflow -d reflow > "${DB_BACKUP}"
else
  echo "--> WARNING: PostgreSQL tools not found. Copying SQLite database fallback if present..."
  if [ -f "./storage/reflow.db" ]; then
    cp "./storage/reflow.db" "${BACKUP_DIR}/reflow_db_${TIMESTAMP}.db"
  fi
fi

# Media Storage Backup
if [ -d "./storage" ]; then
  echo "--> Archiving media storage files..."
  tar -czf "${MEDIA_BACKUP}" --exclude="storage/backups" -C ./ storage
fi

echo "=== Backup Complete ==="
echo "Database dump: ${DB_BACKUP}"
echo "Media archive: ${MEDIA_BACKUP}"
