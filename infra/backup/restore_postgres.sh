#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "Usage: $0 <backup-file> --yes" >&2
  exit 1
fi

BACKUP_FILE="$1"
CONFIRM="${2:-}"

if [ "$CONFIRM" != "--yes" ]; then
  echo "Restore is destructive. Re-run with --yes after reading docs/BACKUP_RESTORE.md." >&2
  exit 1
fi

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.prod.yml}"
POSTGRES_USER="${POSTGRES_USER:-chessju}"
POSTGRES_DB="${POSTGRES_DB:-chessju}"

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
COMPOSE_PATH="$REPO_ROOT/$COMPOSE_FILE"
ENV_PATH="$REPO_ROOT/$ENV_FILE"
BACKUP_PATH="$(realpath "$BACKUP_FILE")"
BACKUP_NAME="$(basename "$BACKUP_PATH")"
CONTAINER_PATH="/tmp/$BACKUP_NAME"

if [ ! -f "$COMPOSE_PATH" ]; then
  echo "Compose file not found: $COMPOSE_PATH" >&2
  exit 1
fi

if [ ! -f "$ENV_PATH" ]; then
  echo "Environment file not found: $ENV_PATH" >&2
  exit 1
fi

if [ ! -f "$BACKUP_PATH" ]; then
  echo "Backup file not found: $BACKUP_PATH" >&2
  exit 1
fi

echo "WARNING: restoring $BACKUP_PATH into database '$POSTGRES_DB'. Existing data may be replaced."

docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH" cp \
  "$BACKUP_PATH" "postgres:$CONTAINER_PATH"

docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH" exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner "$CONTAINER_PATH"

docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH" exec -T postgres \
  rm -f "$CONTAINER_PATH"

echo "Postgres restore completed from $BACKUP_PATH"
