# ChessJU

ChessJU is a custom chess club platform for University of Jordan members.

The current priority is the backend foundation:

- Python FastAPI API
- PostgreSQL database
- Valkey cache/queue/rate-limit layer
- Separate Python worker process
- Local filesystem storage first
- Docker Compose local development
- Flutter/Dart client foundation

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

## Local Demo And Release-Candidate Smoke

Phase 22 adds local-only demo data and repeatable smoke checks for release-candidate QA. These tools
are for development only and must not be used to create production credentials.

Seed demo data after starting Docker and running migrations:

```powershell
cd backend
$env:CHESSJU_DATABASE_URL = "postgresql+psycopg://chessju:chessju_dev_password@localhost:5432/chessju"
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\python.exe scripts\seed_demo_data.py --yes --database-url $env:CHESSJU_DATABASE_URL
```

Seeded local demo accounts:

- `admin@example.com` / `ChangeMe123!`
- `member1@example.com` through `member5@example.com` / `ChangeMe123!`

Run the local API smoke script against the seeded data:

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\smoke_test_api.py `
  --base-url http://localhost:8001 `
  --member-email member4@example.com `
  --member-password ChangeMe123! `
  --friend-email member5@example.com `
  --friend-password ChangeMe123! `
  --admin-email admin@example.com `
  --admin-password ChangeMe123!
```

The smoke script avoids printing tokens or passwords and returns a nonzero exit code for critical
failures. See `docs/SMOKE_TESTS.md` for the full local demo flow.

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

Chess clock backend:

- Casual and pairing-linked clock sessions are supported.
- The client runs the responsive timer locally.
- The backend stores meaningful event snapshots such as start, pause, resume, switch turn, adjust,
  flag, reset, complete, and cancel.
- The backend does not receive every second or tick.

Friends and direct chat backend:

- Users can send, accept, reject, and cancel friend requests.
- Friendships are stored as normalized pairs.
- Blocking cancels pending requests and removes existing friendships.
- Direct conversations require friendship and are text-only in this phase.
- Message deletion is soft deletion, and deleted message bodies are hidden from normal responses.

Realtime and in-app notifications:

- Users can list notifications, mark them read, and manage notification preferences.
- Friend requests, accepted requests, direct messages, analysis completion/failure, and Chess.com
  sync completion/failure can create in-app notifications.
- Published news and announcements create lightweight broadcast realtime events.
- `GET /api/v1/realtime/stream` provides authenticated SSE events for user-targeted updates.
- SSE payloads are small hints; Flutter clients should refetch REST resources for full state.

Backend hardening for Flutter integration:

- Common API errors return `{ "error": { "code", "message", "details", "request_id" } }`.
- Every response includes `X-Request-ID`; clients may send their own safe request ID.
- CORS is configured with `CHESSJU_CORS_ALLOWED_ORIGINS` and related settings.
- Valkey-backed rate limits protect login, register, PGN import, analysis, Chess.com sync, and
  direct message endpoints.
- `/health` is liveness, `/health/db` checks PostgreSQL, and `/health/valkey` checks Valkey.
- See `docs/FLUTTER_API_GUIDE.md` and `docs/SMOKE_TESTS.md` before wiring a Flutter client.

Flutter app foundation:

- The Flutter app lives in `frontend/chessju_app`.
- Web/Desktop local backend URL: `http://localhost:8001`
- Android emulator local backend URL: `http://10.0.2.2:8001`
- iOS simulator on macOS can use `http://localhost:8001`.
- iOS build, signing, TestFlight, and App Store release require macOS with Xcode.
- The app base URL is configurable with `--dart-define=CHESSJU_API_BASE_URL=...`.
- See `docs/FLUTTER_APP.md` for app structure, run commands, auth flow, and current screens.
- The current Flutter vertical slice covers auth, home, news list/detail, tournaments list/detail
  with registration actions, leaderboard, games list/detail, PGN paste import, analysis
  request/report viewing, chess clock UI, friends/direct chat UI, admin dashboard/tournament
  manager UI, notifications, and profile editing.

Run Flutter checks:

```powershell
cd frontend/chessju_app
flutter analyze
flutter test
```

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
standings, automatic Swiss/Round Robin pairing generation, the global JU leaderboard, PGN
paste/upload, normalized game moves, authenticated game
library endpoints, PGN import history, Flutter-ready analysis-board replay data, and basic
Stockfish analysis jobs through the worker, Chess.com public game import, and chess clock sessions
with append-only event logs, friends, blocking, direct conversations, direct text messages, admin
chat moderation listing, in-app notifications, authenticated SSE events, and a Flutter vertical
slice with API client, auth flow, responsive app shell, home/news/tournament/leaderboard/game/
notification/profile screens, game detail replay, PGN paste import, analysis report viewing, a
casual chess clock UI that stores meaningful backend events without sending every tick,
friends/direct chat screens for requests, blocks, conversations, and text messages, and an admin
tournament manager button for Swiss/Round Robin pairing generation, plus local release-candidate
demo seeding and API smoke-test tooling. Advanced tie-breaks, Lichess import, scheduled sync, group
chat, tournament chat, media
messages, push notifications, full WebSocket chat, guaranteed distributed event delivery, PGN file
upload UI, user search/discovery UI, admin player picker/search, drag/drop pairing UI,
SSE-driven chat refresh, engine arrows, evaluation graph behavior, FIDE-certified pairing, advanced
color-history optimization, and dedicated official tournament clock UI are intentionally delayed.

## Notes

The repository may contain old PocketBase files from early experimentation. They are not part of the approved ChessJU backend architecture and should not be used as the core backend.
