# ChessJU Backup And Restore

PostgreSQL is the source of truth for ChessJU. Backups must include Postgres data and local storage
files.

## What To Back Up

- Postgres database dump
- Local file storage volume (`chessju_storage`)
- `.env.production` stored securely outside the repo
- Caddy data volume if preserving existing certificates during server migration

Valkey is not the source of truth. It can be rebuilt from application state.

## Backup Frequency

Recommended MVP starting point:

- daily Postgres backups
- before every deployment
- before every migration
- weekly restore test to a disposable environment

Production backup storage should eventually be off-server. Phase 23 only adds local scripts.

## PowerShell Backup

From the repo root:

```powershell
.\infra\backup\backup_postgres.ps1 `
  -EnvFile ".env.production" `
  -ComposeFile "infra/docker-compose.prod.yml" `
  -BackupDir "backups"
```

The backup file is written under `backups/` with a timestamped name:

```text
backups/chessju-postgres-YYYYMMDD-HHMMSS.dump
```

For the Phase 24 local production dry run, target the isolated Compose project:

```powershell
$env:COMPOSE_PROJECT_NAME = "chessju_prod_dryrun"
.\infra\backup\backup_postgres.ps1 `
  -EnvFile ".env.production.local" `
  -ComposeFile "infra/docker-compose.prod.yml" `
  -BackupDir "backups\dry-run"
```

Phase 24 dry-run result: a timestamped custom-format Postgres dump was created under
`backups/dry-run/`, and Git ignored it through the `backups/` rule.

## Linux/macOS Backup

```sh
ENV_FILE=.env.production \
COMPOSE_FILE=infra/docker-compose.prod.yml \
BACKUP_DIR=backups \
sh infra/backup/backup_postgres.sh
```

## Restore Warning

Restore is destructive. It may replace existing database content. Before restore:

- take a fresh backup of the current database
- stop or pause user traffic if this is a real server
- confirm the target environment
- verify the backup file is the one you intend to restore

## PowerShell Restore

```powershell
.\infra\backup\restore_postgres.ps1 `
  -BackupFile ".\backups\chessju-postgres-YYYYMMDD-HHMMSS.dump" `
  -EnvFile ".env.production" `
  -ComposeFile "infra/docker-compose.prod.yml" `
  -ConfirmRestore
```

## Linux/macOS Restore

```sh
ENV_FILE=.env.production \
COMPOSE_FILE=infra/docker-compose.prod.yml \
sh infra/backup/restore_postgres.sh backups/chessju-postgres-YYYYMMDD-HHMMSS.dump --yes
```

## Test Restore

Do not test restore first on production. Use a disposable local or staging-like environment:

1. Start a fresh compose project with empty volumes.
2. Restore the backup.
3. Run migrations if needed.
4. Run health checks and the API smoke script.
5. Verify key admin and member flows.

Phase 24 did not run destructive restore automatically. To dry-run restore safely later, create a
fresh isolated Compose project and restore into that empty database, not into active dev or
production data.

## Local Storage Backup Notes

Local uploaded files live in the Docker named volume `chessju_storage` in production compose. Back
up this volume along with Postgres. A simple first approach is to copy the mounted storage contents
from a temporary container or use your server backup tool to snapshot Docker volumes.

Do not commit backup files. `backups/`, `*.dump`, `*.sql`, and `*.bak` are ignored by Git.
