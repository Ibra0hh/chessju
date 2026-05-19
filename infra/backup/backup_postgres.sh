#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
POSTGRES_USER="${POSTGRES_USER:-chessju}"
POSTGRES_DB="${POSTGRES_DB:-chessju}"

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
COMPOSE_PATH="$REPO_ROOT/$COMPOSE_FILE"
ENV_PATH="$REPO_ROOT/$ENV_FILE"
BACKUP_PATH="$REPO_ROOT/$BACKUP_DIR"

if [ ! -f "$COMPOSE_PATH" ]; then
  echo "Compose file not found: $COMPOSE_PATH" >&2
  exit 1
fi

if [ ! -f "$ENV_PATH" ]; then
  echo "Environment file not found: $ENV_PATH" >&2
  exit 1
fi

mkdir -p "$BACKUP_PATH"

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_NAME="chessju-postgres-$TIMESTAMP.dump"
CONTAINER_PATH="/tmp/$BACKUP_NAME"

docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file="$CONTAINER_PATH"

docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH" cp \
  "postgres:$CONTAINER_PATH" "$BACKUP_PATH/$BACKUP_NAME"

docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH" exec -T postgres \
  rm -f "$CONTAINER_PATH"

echo "Postgres backup written to $BACKUP_PATH/$BACKUP_NAME"
