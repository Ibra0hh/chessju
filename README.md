# ChessJU

ChessJU is a custom chess club platform for University of Jordan members.

The current priority is the backend foundation:

- Python FastAPI API
- PostgreSQL database
- Valkey cache/queue/rate-limit layer
- Separate Python worker process
- Local filesystem storage first
- Docker Compose local development
- Flutter/Dart clients later

This project does not use Firebase, Supabase, Appwrite, PocketBase, or any backend-as-a-service as the core backend.

## Local Development

Prerequisites:

- WSL2 installed and enabled on Windows
- Docker Desktop installed and configured to use WSL2
- `docker compose` available from the terminal

Copy the example environment file before running local services:

```powershell
Copy-Item .env.example .env
```

Start the local stack:

```powershell
docker compose -f infra/docker-compose.dev.yml up --build
```

API:

```text
http://localhost:8001
```

Home API:

```text
http://localhost:8001/api/v1/home
```

OpenAPI:

```text
http://localhost:8001/docs
```

## Useful Commands

Run tests from the backend package:

```powershell
cd backend
python -m pytest
```

Run Ruff:

```powershell
cd backend
python -m ruff check .
```

Create a migration:

```powershell
cd backend
alembic revision --autogenerate -m "message"
```

Apply migrations:

```powershell
cd backend
alembic upgrade head
```

Local uploads are controlled by `CHESSJU_LOCAL_STORAGE_ROOT`. In Docker development this points to
`/data/storage` inside the API container and is backed by a Docker volume.

## Phase 1 Endpoints

- `GET /health`
- `GET /version`
- `GET /health/db`

Local URLs:

- `http://localhost:8001/health`
- `http://localhost:8001/version`
- `http://localhost:8001/health/db`

## Current Backend Scope

Implemented backend foundations now include auth/users, admin audit logs, files, news,
announcements, home content, time controls, tournaments, and tournament registration MVP behavior.
Rounds, pairings, results, standings, leaderboard, PGN, Stockfish, Chess.com sync, chat, and
frontend code are intentionally delayed.

## Notes

The repository may contain old PocketBase files from early experimentation. They are not part of the approved ChessJU backend architecture and should not be used as the core backend.
