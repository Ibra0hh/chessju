param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$EnvFile = ".env.production",
    [string]$ComposeFile = "infra/docker-compose.prod.yml",
    [string]$PostgresUser = "chessju",
    [string]$PostgresDb = "chessju",
    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmRestore) {
    throw "Restore is destructive. Re-run with -ConfirmRestore after reading docs/BACKUP_RESTORE.md."
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ResolvedComposeFile = Join-Path $RepoRoot $ComposeFile
$ResolvedEnvFile = Join-Path $RepoRoot $EnvFile
$ResolvedBackupFile = Resolve-Path $BackupFile

if (-not (Test-Path $ResolvedComposeFile)) {
    throw "Compose file not found: $ResolvedComposeFile"
}
if (-not (Test-Path $ResolvedEnvFile)) {
    throw "Environment file not found: $ResolvedEnvFile"
}

$BackupName = Split-Path $ResolvedBackupFile -Leaf
$ContainerPath = "/tmp/$BackupName"

Write-Warning "This will restore $ResolvedBackupFile into database '$PostgresDb'. Existing data may be replaced."

docker compose --env-file $ResolvedEnvFile -f $ResolvedComposeFile cp `
    $ResolvedBackupFile "postgres:$ContainerPath"

docker compose --env-file $ResolvedEnvFile -f $ResolvedComposeFile exec -T postgres `
    pg_restore -U $PostgresUser -d $PostgresDb --clean --if-exists --no-owner $ContainerPath

docker compose --env-file $ResolvedEnvFile -f $ResolvedComposeFile exec -T postgres `
    rm -f $ContainerPath

Write-Host "Postgres restore completed from $ResolvedBackupFile"
