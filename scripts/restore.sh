#!/usr/bin/env bash
# ==============================================================================
# Reflow — Database & Media Storage Restore Script
# ==============================================================================
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <path_to_db_backup.sql> [path_to_media_backup.tar.gz]"
  echo "Example: $0 ./storage/backups/reflow_db_20260901_120000.sql ./storage/backups/reflow_media_20260901_120000.tar.gz"
  exit 1
fi

DB_FILE="$1"
MEDIA_FILE="$2"

if [ ! -f "${DB_FILE}" ]; then
  echo "Error: Database backup file '${DB_FILE}' not found."
  exit 1
fi

echo "=============================================================================="
echo "WARNING: DESTRUCTIVE RESTORE OPERATION"
echo "This action will overwrite current data in the Reflow PostgreSQL database."
echo "Target DB File: ${DB_FILE}"
if [ -n "${MEDIA_FILE}" ]; then
  echo "Target Media File: ${MEDIA_FILE}"
fi
echo "=============================================================================="

if [ "${CONFIRM_RESTORE}" != "true" ]; then
  read -p "Are you sure you want to proceed with restore? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore aborted by user."
    exit 0
  fi
fi

echo "--> Restoring database..."
if command -v docker >/dev/null 2>&1 && docker ps | grep -q reflow_postgres; then
  docker exec -i reflow_postgres psql -U reflow -d reflow < "${DB_FILE}"
elif command -v psql >/dev/null 2>&1; then
  psql -U reflow -d reflow < "${DB_FILE}"
else
  echo "Error: Neither docker container reflow_postgres nor psql command is available."
  exit 1
fi

if [ -n "${MEDIA_FILE}" ] && [ -f "${MEDIA_FILE}" ]; then
  echo "--> Restoring media storage..."
  tar -xzf "${MEDIA_FILE}" -C ./
fi

echo "=== Reflow Restore Completed Successfully ==="
