# ChessJU Permanent Project Instructions

This file contains the standing instructions for future Codex work on the ChessJU repository.

Follow these instructions unless Ibrahim explicitly overrides them in the current task.

## Project Name

ChessJU

## Project Owner

Ibrahim  
Data Science / Information Technology student  
University of Jordan

## Project Summary

ChessJU is a custom chess club platform for University of Jordan members.

The platform will eventually include:

- Flutter/Dart mobile app
- Flutter/Dart web app
- Flutter/Dart admin app or dashboard
- Custom Python FastAPI backend
- PostgreSQL database
- Valkey cache/queue/rate-limit layer
- Separate Python worker for background jobs
- Local filesystem storage first
- SSE realtime first
- WebSocket later for chat/live features

The backend is the current priority.

ChessJU features:

- User accounts
- Profiles
- Roles
- Preferences
- News
- Announcements
- Tournaments
- Registration
- Manual pairings first
- Results
- Standings
- JU leaderboard
- Chess clock
- PGN upload
- PGN parsing
- Game library
- Basic analysis board support
- Basic Stockfish analysis jobs
- Chess.com import later
- Friends/chat later
- Personalization later
- Admin audit logs
- Realtime tournament/news/leaderboard/analysis updates

## Custom Backend Rule

Do not use any backend-as-a-service as the core backend.

Forbidden as core backend:

- Firebase
- Supabase
- Appwrite
- PocketBase
- Any BaaS platform

The project must be fully custom and self-controlled.

Allowed:

- Open-source libraries
- Open-source databases
- Open-source infrastructure tools
- Local development tools
- Docker/containers
- PostgreSQL
- Valkey
- Caddy
- Stockfish
- python-chess

## Approved Stack

Frontend later:

- Flutter
- Dart

Backend now:

- Python
- Prefer Python 3.12 unless the local environment requires a different version
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Valkey
- RQ or another simple Valkey-backed queue after discussion
- python-chess
- Stockfish for basic analysis jobs
- Local filesystem storage first
- Docker Compose
- Docker Desktop with WSL2 on Windows
- SSE first for realtime
- WebSocket later for chat
- pytest
- httpx test client
- Ruff
- mypy or pyright optional later

## Architecture Principles

Use a modular monolith.

Do not use microservices at the beginning.

PostgreSQL is the source of truth.

Valkey is not the source of truth.

Valkey may be used only for:

- cache
- rate limits
- queues
- temporary realtime state
- presence later
- short-lived data

File storage is only for binary files:

- avatars
- PGN files
- news images
- tournament images
- exports

Store file metadata in PostgreSQL.

The backend owns official business logic:

- tournament registration
- capacity rules
- manual pairings
- result submission
- standings
- leaderboard
- roles
- admin permissions
- game records
- PGN parsing
- audit logging

The frontend must not calculate official:

- tournament standings
- leaderboard ranks
- tournament results
- pairing state
- admin permissions

Use database transactions for critical flows.

Use database constraints, not only application checks.

Use soft delete for important business records.

Use audit logs for admin actions.

Use background jobs for slow work.

Use small realtime events and let clients refetch full state.

## Repository Structure

Use this structure unless Ibrahim approves a change:

```text
chessju/
  backend/
    app/
      main.py
      config.py
      database.py
      auth/
      users/
      admin/
      tournaments/
      news/
      leaderboard/
      files/
      games/
      pgn/
      analysis/
      realtime/
      common/
    alembic/
    tests/
    Dockerfile
    pyproject.toml

  worker/
    jobs/
    chess_engine/
    chesscom/
    Dockerfile

  infra/
    docker-compose.dev.yml
    docker-compose.prod.yml
    Caddyfile
    backup/

  docs/
    ARCHITECTURE.md
    ROADMAP.md
    DATABASE.md
    API.md
    SECURITY.md
    SETUP.md

  README.md
  .env.example
  .gitignore
  AGENTS.md
```

## MVP Scope

MVP should focus on:

1. Backend foundation
2. Health/version endpoints
3. PostgreSQL connection
4. Alembic migrations
5. Docker Compose local environment
6. Custom JWT auth
7. Users/profiles/roles
8. Admin authorization
9. Admin audit logs
10. News and announcements
11. Tournament CRUD
12. Tournament registration
13. Manual pairings
14. Results
15. Basic standings
16. Basic JU leaderboard
17. Local file metadata/storage
18. PGN upload
19. PGN parsing
20. Game library
21. SSE event foundation

Delay until later:

- Chat
- WebSockets
- advanced Stockfish review behavior
- Chess.com sync
- automatic Swiss pairing
- advanced tie-breaks
- production monitoring stack
- external object storage
- Kubernetes
- microservices

## Analysis Board Feature

ChessJU will have a basic original chess analysis board.

It may be inspired by common chess analysis board concepts, but do not copy Chess.com branding, assets, exact layout, proprietary UI, or proprietary Game Review behavior.

Version 1 analysis board support is backend-first:

- User can paste PGN
- User can upload PGN file
- Backend validates PGN size and format
- Backend parses PGN using python-chess
- Backend extracts metadata
- Backend stores game
- Backend stores PGN import record
- Backend returns normalized JSON for Flutter replay

Extract metadata when available:

- white player
- black player
- result
- event
- site
- date
- round
- ECO
- time control

Extract move data:

- move number
- side to move
- SAN notation
- UCI notation
- FEN before move
- FEN after move
- check/checkmate if available
- comments if present

Flutter will later use the normalized JSON to render:

- chess board
- move list
- next/previous buttons
- jump to move
- current FEN
- game details panel
- highlighted last move

The first PGN phase should not include Stockfish analysis.

The basic Stockfish phase may include:

- analysis_jobs
- analysis_reports
- engine name/version
- depth/time settings
- evaluation per move
- best move
- candidate lines
- mistake/blunder classification
- accuracy estimate
- evaluation bar support
- analysis completed event

Advanced review behavior, cloud-scale analysis, and exact Game Review clone behavior remain later
work.

## Flutter API Design Rules

Design backend APIs so Flutter/Dart clients can consume them cleanly.

Use REST JSON APIs first.

Prefer:

- stable response shapes
- explicit request schemas
- explicit response schemas
- ISO 8601 timestamps
- UUID identifiers
- predictable pagination metadata
- predictable error response format
- clear auth errors
- clear permission errors
- multipart upload support for files
- normalized move data for board replay

Do not require Flutter clients to infer official business state from partial data.

Do not require Flutter clients to calculate official standings, leaderboard ranks, results, or admin permissions.

## Security Rules

Never commit secrets.

Never hardcode:

- database URLs
- JWT secrets
- passwords
- API keys
- admin credentials

Use environment variables.

Use `.env.example` with safe placeholder values only.

Authentication:

- custom JWT auth for MVP
- short-lived access tokens
- refresh tokens stored hashed
- refresh token rotation
- password hashing with Argon2id or bcrypt
- email verification later if not in first auth version

Authorization:

- role-based authorization
- object-level authorization
- admin route protection
- member/admin/arbiter/super_admin roles

Every route that accesses an object by ID must check whether the current user is allowed to access it.

Every admin mutation must write an admin audit log.

Rate limit:

- login
- signup
- password reset
- PGN upload
- analysis jobs later
- Chess.com sync later
- chat later

Uploads:

- validate file size
- validate MIME type
- validate extension
- validate PGN content
- do not trust client filenames
- store file metadata in PostgreSQL

## Database Rules

Use UUID primary keys unless there is a strong reason not to.

Use `created_at` and `updated_at` where appropriate.

Use `deleted_at` for soft delete where appropriate.

Use foreign keys.

Use unique constraints.

Use indexes based on actual query needs.

Use transactions for:

- registration capacity
- result submission
- leaderboard updates
- role/admin changes
- PGN import plus game creation
- audit log mutations

Do not create all future tables in the first migration unless Ibrahim approves.

Build schema in phases.

## First Database Modules

Phase 1 foundation may create no business tables except migration sanity if needed.

Phase 2 auth/users:

- users
- profiles
- roles
- user_roles
- user_preferences
- refresh_tokens

Phase 3 admin:

- admin_action_logs

Phase 4 news:

- files
- articles
- announcements

Phase 5 tournaments:

- time_controls
- tournaments
- tournament_registrations

Phase 6 realtime:

- outbox_events

Phase 7 pairings/results:

- rounds
- pairings
- games

Phase 8 leaderboard:

- seasons
- player_ratings
- rating_events
- leaderboard_snapshots

Phase 10 PGN:

- pgn_imports
- game_moves if needed

Phase 9 Stockfish analysis:

- analysis_jobs
- analysis_reports
- analysis_move_evaluations

## API Rules

Use REST JSON APIs first.

Base path:

```text
/api/v1
```

Operational endpoints first:

- `GET /health`
- `GET /version`
- `GET /health/db`
- `GET /health/valkey` later

Do not add domain APIs before the foundation is working.

Use clear request/response schemas.

Use consistent error responses.

Do not leak internal errors to users.

Generate OpenAPI through FastAPI.

Design responses so Flutter can consume them cleanly.

## Realtime Rules

Use SSE first for:

- tournament updates
- registration updates
- announcements
- leaderboard updates
- analysis completed later

Use WebSocket later for:

- chat
- live interactive features
- presence

Realtime events should be small.

Example:

```json
{
  "type": "tournament.updated",
  "tournament_id": "uuid",
  "version": 3,
  "changed_at": "timestamp"
}
```

The client should refetch full state after receiving most realtime events.

## Worker Rules

Use a separate worker package.

Worker jobs include or may later include:

- parse_pgn_file
- analyze_game_with_stockfish
- sync_chesscom_games
- recompute_leaderboard
- send_notification
- generate_tournament_report
- cleanup_expired_tokens
- cleanup_old_uploads

Do not run slow jobs inside normal API requests.

Do not run Stockfish inside the request/response cycle.

## Coding Standards

Use clean, boring, maintainable code.

Prefer explicit code over magic.

Use type hints.

Use Pydantic schemas for request/response validation.

Separate routers, services, models, and schemas.

Keep business logic out of route handlers when possible.

Use dependency injection for database sessions/current user.

Use consistent naming.

Use small commits/steps.

Do not over-engineer.

Do not add unnecessary abstractions.

Do not build features before the current phase is tested.

Do not delete, overwrite, or rename existing user files without explaining the change first.

Prefer additive changes during setup.

## Testing Standards

Use pytest.

Write tests for:

- health endpoints
- config loading
- database connection
- auth logic
- role checks
- object-level authorization
- tournament registration
- capacity race conditions
- duplicate registration
- admin audit logs
- PGN parser
- file upload validation
- leaderboard calculation

Dangerous logic must have tests before moving on.

## Documentation Rules

Keep docs updated in `/docs`.

Important docs:

- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DATABASE.md`
- `API.md`
- `SECURITY.md`
- `SETUP.md`

README should explain:

- project purpose
- local setup
- environment variables
- Docker Compose commands
- test commands
- migration commands

## Do Not Build Yet

Do not build these until Ibrahim explicitly approves the phase:

- Chat
- WebSocket chat
- advanced Stockfish review behavior
- Chess.com sync
- automatic Swiss pairing
- advanced tie-breaks
- Kubernetes
- microservices
- production monitoring stack
- MinIO/Garage external object storage
- Keycloak
- payment features

## First Setup Rule

Before creating files or running commands, wait for the exact phrase:

```text
APPROVED: START SETUP
```

After that, do only Phase 1 foundation:

1. Inspect current directory
2. Check OS/tools
3. Before creating the repository structure, inspect the current directory and determine whether it is already the ChessJU project root
4. Do not accidentally create a nested `chessju/chessju` directory
5. If the current directory is empty, create the planned structure there
6. If the current directory already contains project files, explain what you found before modifying anything
7. Create repository structure
8. Create FastAPI backend shell
9. Add config
10. Add database setup
11. Add Alembic setup
12. Add Docker Compose for api, postgres, valkey, worker
13. Add `.env.example`
14. Add health/version endpoints
15. Add basic tests
16. Add README setup commands
17. Run tests
18. Report exactly what changed
19. Stop and wait for approval before auth

## End Of AGENTS.md
