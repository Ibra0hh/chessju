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

Stockfish analysis settings:

- `CHESSJU_STOCKFISH_PATH`
- `CHESSJU_STOCKFISH_DEPTH_DEFAULT`
- `CHESSJU_STOCKFISH_DEPTH_MAX`
- `CHESSJU_ANALYSIS_MAX_PLIES`
- `CHESSJU_ANALYSIS_JOB_TIMEOUT_SECONDS`

The worker image installs Stockfish and consumes the Valkey/RQ `analysis` queue. Analysis jobs run
outside API request handlers.

Chess.com public import settings:

- `CHESSJU_CHESSCOM_SYNC_MAX_MONTHS`
- `CHESSJU_CHESSCOM_SYNC_TIMEOUT_SECONDS`
- `CHESSJU_CHESSCOM_USER_AGENT`

Chess.com sync uses only public read-only data. ChessJU never asks for Chess.com passwords and does
not scrape pages. Sync jobs run in the worker and imported PGNs reuse the existing game library,
normalized move storage, and analysis endpoints.

Chesskit may be used only as a conceptual reference for common chess-review ideas. Do not copy its
AGPL-3.0 code, UI layout, assets, names, branding, files, or exact wording into ChessJU.

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
announcements, home content, time controls, tournaments, tournament registration MVP behavior,
manual rounds, manual pairings, result entry, linked tournament game records, basic tournament
standings, the global JU leaderboard, PGN paste/upload, normalized game moves, authenticated game
library endpoints, PGN import history, Flutter-ready analysis-board replay data, and basic
Stockfish analysis jobs through the worker, and Chess.com public game import. Chat, frontend code,
automatic pairing, advanced tie-breaks, Lichess import, scheduled sync, and advanced game review
behavior are intentionally delayed.

## Notes

The repository may contain old PocketBase files from early experimentation. They are not part of the approved ChessJU backend architecture and should not be used as the core backend.
