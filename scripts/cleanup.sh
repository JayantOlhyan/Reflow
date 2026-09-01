#!/usr/bin/env bash
# ==============================================================================
# Reflow — Disk & Storage Safe Cleanup Script
# ==============================================================================
set -e

STORAGE_DIR="${STORAGE_DIR:-./storage}"

echo "=== Reflow Storage Cleanup Starting ==="

if [ -d "${STORAGE_DIR}" ]; then
  echo "--> Cleaning up temporary health checks and orphan transcode files..."
  find "${STORAGE_DIR}" -type f -name ".health_check*" -delete 2>/dev/null || true
  find "${STORAGE_DIR}" -type f -name "*.tmp" -mtime +1 -delete 2>/dev/null || true
  find "${STORAGE_DIR}" -type f -name "temp_chunk_*" -mtime +1 -delete 2>/dev/null || true
  echo "--> Temporary transcode files cleaned."
else
  echo "--> Storage directory ${STORAGE_DIR} does not exist. Skipping."
fi

echo "=== Reflow Storage Cleanup Complete ==="
