# ChessJU Production Checklist

Use this checklist before any real production deployment.

## Environment And Secrets

- [ ] `.env.production` exists on the server and is not committed
- [ ] `CHESSJU_ENVIRONMENT=production`
- [ ] `CHESSJU_DEBUG=false`
- [ ] `CHESSJU_JWT_SECRET_KEY` is strong and unique
- [ ] `POSTGRES_PASSWORD` is strong and matches `CHESSJU_DATABASE_URL`
- [ ] `CHESSJU_CHESSCOM_USER_AGENT` includes a valid contact
- [ ] no real secrets are present in docs, Git history, or screenshots

## Network And CORS

- [ ] Caddy is the only public HTTP/HTTPS entrypoint
- [ ] API does not expose a direct public port
- [ ] Postgres does not expose a public port
- [ ] Valkey does not expose a public port
- [ ] DNS points to the server
- [ ] HTTPS works through Caddy
- [ ] `CHESSJU_CORS_ALLOWED_ORIGINS` is locked to production origins
- [ ] wildcard CORS is not used with credentials enabled

## Database And Backups

- [ ] migrations run successfully
- [ ] `alembic current` shows the expected head
- [ ] Postgres backup script runs
- [ ] restore process has been tested in a disposable environment
- [ ] local storage volume backup strategy exists
- [ ] backup files are not committed

## Admin And Access

- [ ] first admin account is created safely
- [ ] no hidden admin creation endpoint exists
- [ ] demo seed script was not run against production
- [ ] admin can login
- [ ] non-admin cannot access admin dashboard/API

## Runtime Checks

- [ ] `docker compose --env-file .env.production -f infra/docker-compose.prod.yml config` passes
- [ ] local dry-run config passes with `-p chessju_prod_dryrun`
- [ ] local dry-run stack starts without colliding with the dev stack
- [ ] `docker compose --env-file .env.production -f infra/docker-compose.prod.yml ps` is healthy
- [ ] `/health` passes
- [ ] `/version` passes
- [ ] `/health/db` passes
- [ ] `/health/valkey` passes
- [ ] API smoke tests pass through Caddy against the target environment
- [ ] worker is running
- [ ] Stockfish path is valid in the worker

## Safety Settings

- [ ] rate limits enabled
- [ ] request IDs visible in responses
- [ ] errors use the standard envelope and do not expose stack traces
- [ ] file responses do not expose internal storage paths
- [ ] notification/realtime payloads do not expose secrets or raw PGN

## Flutter Web

- [ ] Flutter web build uses the production API URL
- [ ] build output verified locally
- [ ] serving strategy is chosen: Caddy static files or separate hosting
- [ ] iOS build/signing is deferred to macOS with Xcode

## Release Decision

- [ ] latest backend tests pass
- [ ] latest Ruff check passes
- [ ] latest Flutter analyze/test/build web pass
- [ ] production-style dry-run passes locally
- [ ] release candidate tag is pushed only after dry-run passes
- [ ] rollback plan is written
- [ ] backup taken immediately before deployment
- [ ] Ibrahim explicitly approved deploying to the real server
