# ChessJU Project State

Checkpoint date: 2026-05-19

## Project Identity

- Project name: ChessJU
- Owner: Ibrahim
- Purpose: custom chess club platform for University of Jordan members

ChessJU is backend-first right now. Flutter/Dart mobile, web, and admin clients are planned later.

## Architecture

- Fully custom backend
- No Firebase
- No Supabase
- No Appwrite
- No PocketBase
- No backend-as-a-service as the core backend
- FastAPI backend
- PostgreSQL as the source of truth
- Valkey for cache, queues, rate limits, and temporary state only
- Separate Python worker package for background jobs
- Docker Compose local development environment
- Local filesystem storage first
- Flutter/Dart frontend later

## Completed Phases

### Phase 1: Backend Foundation

- FastAPI backend foundation
- Health endpoint
- Version endpoint
- Database health endpoint
- Docker Compose local stack
- PostgreSQL service
- Valkey service

### Phase 2: Auth And Users

- Custom JWT authentication
- User registration and login
- Refresh token rotation
- Logout and refresh token revocation
- Users
- Profiles
- Roles
- User roles
- User preferences
- Hashed refresh tokens

### Phase 3: Admin Foundation

- Admin role guards
- Admin identity endpoint
- Admin audit log table
- Paginated audit log listing
- Reusable audit logging service
- Sensitive-field redaction rules

### Phase 4: Files, News, Announcements, Home

- Local filesystem file metadata/storage foundation
- Admin file upload endpoint
- News/articles
- Announcements
- Public home endpoint
- Public latest news and announcements
- Admin mutations integrated with audit logs

### Phase 5: Tournaments MVP

- Time controls
- Tournament records
- Public tournament list/detail
- Admin tournament management
- Tournament registration
- Capacity checks
- Waitlist behavior
- Registration cancellation
- Home endpoint includes upcoming tournaments

### Phase 6: Rounds, Pairings, Results, Standings

- Tournament rounds
- Manual pairings
- Bulk manual pairings
- Result submission
- Tournament game records
- Public round and pairing display
- Live tournament standings
- Basic tournament scoring rules
- Admin mutations integrated with audit logs

### Phase 7: JU Leaderboard

- Seasons
- Player ratings table
- Rating events table
- Leaderboard snapshots
- Admin season management
- Admin leaderboard recompute
- Public leaderboard endpoints
- Home leaderboard preview
- Snapshot replacement behavior on recompute

### Phase 8: PGN Upload, Game Library, Analysis Board Backend

- PGN paste
- PGN upload
- PGN validation and parsing with python-chess
- Shared game library
- Normalized `game_moves`
- PGN import history
- Flutter-ready board replay data
- SAN, UCI, FEN before, FEN after, comments, check, and checkmate flags
- Basic analysis-board backend without engine evaluation

### Phase 9: Stockfish Analysis Jobs

- Stockfish analysis jobs
- Analysis reports
- Move evaluations
- RQ/Valkey worker queue behavior
- Analysis request/status/report endpoints
- Stockfish runs in the worker, not normal API request handlers
- Simple ChessJU move classifications:
  - best
  - excellent
  - good
  - inaccuracy
  - mistake
  - blunder
  - forced
  - unknown
- Approximate accuracy behavior
- Flutter-ready analysis report shape for later evaluation bar, graph, best move, principal variation, and summary UI

### Phase 10: Chess.com Public Game Import

- Chess.com account connection
- Public Chess.com profile verification/fetching
- Chess.com sync jobs
- Worker `chesscom` queue
- Public monthly archive fetching through Chess.com's public API
- Imported games reuse existing `games`, `game_moves`, and `pgn_imports`
- Imported games use `source = chesscom_import`
- Imported games appear in the existing game library
- Imported games integrate with the existing Stockfish analysis flow
- No Chess.com passwords
- No private Chess.com APIs
- No scraping

## Current Database State

Current Alembic head:

- `0010_chesscom_import`

Main database tables:

- `users`
- `profiles`
- `roles`
- `user_roles`
- `user_preferences`
- `refresh_tokens`
- `admin_action_logs`
- `files`
- `articles`
- `announcements`
- `time_controls`
- `tournaments`
- `tournament_registrations`
- `rounds`
- `pairings`
- `games`
- `seasons`
- `player_ratings`
- `rating_events`
- `leaderboard_snapshots`
- `game_moves`
- `pgn_imports`
- `analysis_jobs`
- `analysis_reports`
- `analysis_move_evaluations`
- `chesscom_accounts`
- `chesscom_sync_jobs`
- `chesscom_imported_games`

## Current API State

Endpoint groups currently implemented:

- Health/version endpoints
- Auth endpoints
- `users/me` profile and preferences endpoints
- Admin identity and audit log endpoints
- Admin files endpoint
- Public news endpoints
- Admin news endpoints
- Public announcement endpoints
- Admin announcement endpoints
- Home endpoint
- Public tournament endpoints
- Authenticated tournament registration endpoints
- Admin tournament and time-control endpoints
- Public rounds, pairings, and standings endpoints
- Admin rounds, pairings, and results endpoints
- Public JU leaderboard endpoints
- Admin leaderboard endpoints
- Game library and PGN endpoints
- Analysis job/report endpoints
- Chess.com integration endpoints

## Current Worker And Queue State

- Worker package exists under `worker/`
- Worker runs as a Docker Compose service
- Valkey/RQ is used for queue transport
- `analysis` queue exists for Stockfish analysis jobs
- `chesscom` queue exists for Chess.com sync jobs
- Stockfish analysis jobs run in the worker
- Chess.com sync jobs run in the worker

## Current Test And Quality Status

Latest known verification at this checkpoint:

- pytest: `209 passed`
- Ruff: passed
- Alembic current head: `0010_chesscom_import`
- Docker stack status:
  - API running on `http://localhost:8001`
  - PostgreSQL running and healthy
  - Valkey running
  - Worker running

## Current GitHub State

- Repository: https://github.com/Ibra0hh/chessju
- Branch: `main`
- Latest Phase 10 commit: `5312ffe30ecc1940aa4ebb2affb0529551a1bb74`
- Git status before creating this checkpoint: clean

## Important Permanent Rules

- PostgreSQL is the source of truth.
- Valkey is not the source of truth.
- Valkey may be used for cache, queues, rate limits, presence later, and temporary state only.
- Admin mutations must write audit logs.
- The frontend must not calculate official tournament standings.
- The frontend must not calculate official JU leaderboard ranks.
- Stockfish must run through worker/background jobs, not inside normal API request handlers.
- Chess.com integration must use public read-only API data only.
- Do not ask for Chess.com passwords.
- Do not store Chess.com credentials.
- Do not scrape Chess.com pages.
- Do not commit secrets.
- Do not commit `.env`.
- Do not use Firebase, Supabase, Appwrite, PocketBase, or any BaaS as the core backend.

## Not Implemented Yet

- Chess clock backend
- Friends/chat
- Flutter frontend
- Automatic Swiss pairing
- Automatic round-robin generation
- Advanced tie-breaks
- Production monitoring stack
- External object storage
- Push notifications
- Scheduled Chess.com sync

## Recommended Next Phase

Recommended next phase: Phase 11, Chess Clock Backend.

Reasoning:

- It is a core chess app feature.
- It is independent from Stockfish and Chess.com import.
- It can support both casual use and tournament pairings.
- The backend should store meaningful clock events only, not every tick.
- A clock foundation can later connect to tournament pairings without changing the existing game library or analysis architecture.
