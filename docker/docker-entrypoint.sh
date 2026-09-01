#!/usr/bin/env bash
set -e

mkdir -p /app/storage

# Run Alembic migrations if alembic config exists
if [ -f "alembic.ini" ]; then
  echo "--> Running Alembic database migrations..."
  alembic upgrade head || echo "--> Alembic migration notice: Continuing with init_db..."
fi

# Execute container command
exec "$@"
