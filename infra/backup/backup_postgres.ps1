param(
    [string]$EnvFile = ".env.production",
    [string]$ComposeFile = "infra/docker-compose.prod.yml",
    [string]$BackupDir = "backups",
    [string]$PostgresUser = "chessju",
    [string]$PostgresDb = "chessju"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ResolvedComposeFile = Join-Path $RepoRoot $ComposeFile
$ResolvedEnvFile = Join-Path $RepoRoot $EnvFile
$ResolvedBackupDir = Join-Path $RepoRoot $BackupDir

if (-not (Test-Path $ResolvedComposeFile)) {
    throw "Compose file not found: $ResolvedComposeFile"
}
if (-not (Test-Path $ResolvedEnvFile)) {
    throw "Environment file not found: $ResolvedEnvFile"
}

New-Item -ItemType Directory -Force -Path $ResolvedBackupDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupName = "chessju-postgres-$Timestamp.dump"
$ContainerPath = "/tmp/$BackupName"
$BackupPath = Join-Path $ResolvedBackupDir $BackupName

docker compose --env-file $ResolvedEnvFile -f $ResolvedComposeFile exec -T postgres `
    pg_dump -U $PostgresUser -d $PostgresDb --format=custom --file=$ContainerPath

docker compose --env-file $ResolvedEnvFile -f $ResolvedComposeFile cp `
    "postgres:$ContainerPath" $BackupPath

docker compose --env-file $ResolvedEnvFile -f $ResolvedComposeFile exec -T postgres `
    rm -f $ContainerPath

Write-Host "Postgres backup written to $BackupPath"
