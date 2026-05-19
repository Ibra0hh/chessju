# ChessJU Production Deployment Foundation

Phase 23 prepares production-style deployment files and validation only. Do not deploy to a real
paid server until Ibrahim explicitly approves it.

## 1. Server Requirements

Recommended starting point for a small MVP server:

- Linux server with Docker Engine and Docker Compose plugin
- 2 CPU cores minimum
- 2-4 GB RAM minimum
- 20+ GB disk, with room for Postgres backups and local uploads
- Public DNS record pointing to the server if HTTPS is needed
- Firewall allowing only SSH, HTTP `80`, and HTTPS `443`

PostgreSQL remains the source of truth. Valkey is for cache, queues, and rate limits only.

## 2. Install Docker

Install Docker Engine and verify:

```sh
docker --version
docker compose version
```

Use the official Docker installation instructions for the server OS.

## 3. Clone The Repo

```sh
git clone https://github.com/Ibra0hh/chessju.git
cd chessju
```

## 4. Create `.env.production`

Copy the production template:

```sh
cp .env.production.example .env.production
```

Then edit `.env.production`:

- replace `POSTGRES_PASSWORD`
- replace `CHESSJU_DATABASE_URL` with the matching password
- replace `CHESSJU_JWT_SECRET_KEY` with a strong random value
- set `CADDY_SITE_ADDRESS`
- set `CADDY_ACME_EMAIL`
- set `CHESSJU_CORS_ALLOWED_ORIGINS`
- set `CHESSJU_CHESSCOM_USER_AGENT` contact text

Never commit `.env.production`.

## 5. Configure Domain And Caddy

Production HTTPS:

```env
CADDY_SITE_ADDRESS=chessju.example.com
CADDY_ACME_EMAIL=admin@example.com
```

Caddy will request and renew HTTPS certificates automatically when:

- DNS points to the server
- ports `80` and `443` are reachable
- `CADDY_SITE_ADDRESS` is a real public domain

Local-only config validation:

```env
CADDY_SITE_ADDRESS=http://localhost
```

This disables automatic HTTPS for the local placeholder address.

## 6. Validate Compose Configuration

```sh
docker compose --env-file .env.production -f infra/docker-compose.prod.yml config
```

The production compose stack includes:

- `caddy`: only public entrypoint, ports `80` and `443`
- `api`: internal only, reverse proxied by Caddy
- `worker`: background jobs
- `postgres`: internal only
- `valkey`: internal only

API, Postgres, and Valkey are not publicly exposed.

## 7. Start Production Compose

After approval for a real server deployment:

```sh
docker compose --env-file .env.production -f infra/docker-compose.prod.yml up --build -d
```

Check services:

```sh
docker compose --env-file .env.production -f infra/docker-compose.prod.yml ps
```

## 8. Run Migrations

```sh
docker compose --env-file .env.production -f infra/docker-compose.prod.yml run --rm api \
  alembic upgrade head
```

Confirm current head:

```sh
docker compose --env-file .env.production -f infra/docker-compose.prod.yml run --rm api \
  alembic current
```

## 9. Create An Admin Safely

Do not run demo seed scripts in production.

Safe local production-style method:

1. Register a normal user through the public API or Flutter app.
2. Assign the admin role directly in Postgres from the server console.
3. Re-login so the access token contains the admin role.

Example SQL:

```sql
insert into user_roles (user_id, role_id, assigned_by)
select u.id, r.id, null
from users u
join roles r on r.name in ('admin', 'super_admin')
where u.email = 'admin@example.com'
on conflict do nothing;
```

There is no hidden admin creation endpoint.

## 10. Verify Health Endpoints

Through Caddy:

```sh
curl -i https://chessju.example.com/health
curl -i https://chessju.example.com/version
curl -i https://chessju.example.com/health/db
curl -i https://chessju.example.com/health/valkey
```

For local placeholder validation, use `http://localhost`.

## 11. Flutter Web Build

Do not deploy Flutter web in Phase 23. Build only:

```sh
cd frontend/chessju_app
flutter build web --dart-define=CHESSJU_API_BASE_URL=https://chessju.example.com
```

Build output appears in:

```text
frontend/chessju_app/build/web
```

Future serving options:

- serve Flutter web from Caddy as static files
- serve Flutter web from separate static hosting
- keep API behind the same Caddy domain

Current limitation: the Flutter API base URL is compile-time configuration through
`--dart-define`. A future improvement can add runtime config for web builds.

## 12. Rollback Basics

Simple rollback for a bad app build:

```sh
git log --oneline
git checkout <previous-good-commit>
docker compose --env-file .env.production -f infra/docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f infra/docker-compose.prod.yml run --rm api \
  alembic current
```

Database rollback is not automatic. Restore only from a known-good backup after reading
`docs/BACKUP_RESTORE.md`.

## 13. Local Validation Commands

These are safe and do not deploy to a real server:

```sh
docker compose -f infra/docker-compose.prod.yml config
docker compose -f infra/docker-compose.dev.yml config
```
