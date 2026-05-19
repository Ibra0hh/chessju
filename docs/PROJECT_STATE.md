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

### Phase 11: Chess Clock Backend

- Casual chess clock sessions
- Pairing-linked official clock sessions
- Tournament-linked clock metadata support
- Clock session recovery state
- Append-only clock event log
- Start, pause, resume, switch-turn, adjust, flag, reset, complete, and cancel actions
- Admin clock session listing
- Pairing players can view official pairing clocks
- Backend stores meaningful snapshots only, not every tick

### Phase 12: Friends And Direct Chat Backend

- Friend requests
- Friend acceptance, rejection, and cancellation
- Normalized friendships
- Blocking and unblocking users
- Blocking cancels pending requests and removes existing friendship rows
- Direct conversations between friends
- Text-only direct messages
- Conversation read state
- Soft-deleted messages with sanitized user responses
- Admin social/chat listing endpoints
- Admin message moderation audit log action

### Phase 13: Realtime Events And In-App Notifications

- In-app notifications
- Notification preferences
- Unread notification counts
- Mark-one and mark-all read behavior
- PostgreSQL-backed realtime event outbox
- Authenticated SSE stream endpoint
- Admin notification listing
- Admin realtime event listing
- Friend request notification integration
- Direct message notification integration
- Analysis completed/failed notification integration
- Chess.com sync completed/failed notification integration
- Broadcast realtime events for published news and announcements

### Phase 14: Backend Hardening And API Polish

- Standard API error response shape
- Request ID middleware and `X-Request-ID` response headers
- Environment-backed CORS configuration for future Flutter web/admin
- Valkey-backed rate-limit foundation
- Rate limits on login, register, PGN import, analysis request, Chess.com sync, and message send
- `/health/valkey` readiness endpoint
- OpenAPI tag organization
- Shared pagination metadata helper for future response standardization
- Flutter API integration guide
- Manual smoke-test guide
- Public/admin security review documentation

## Current Database State

Current Alembic head:

- `0013_realtime_notifications`

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
- `clock_sessions`
- `clock_events`
- `friend_requests`
- `friendships`
- `blocked_users`
- `conversations`
- `conversation_members`
- `messages`
- `message_reads`
- `notifications`
- `notification_preferences`
- `realtime_events`

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
- Chess clock session and event endpoints
- Friends, blocks, direct conversation, and message endpoints
- Admin social/chat moderation listing endpoints
- Notification and notification preference endpoints
- Authenticated SSE realtime stream endpoint
- Admin notification and realtime event listing endpoints
- Standard error responses with request IDs
- Valkey health endpoint

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

- pytest: `306 passed`
- Ruff: passed
- Alembic current head: `0013_realtime_notifications`
- Docker stack status:
  - API running on `http://localhost:8001`
  - PostgreSQL running and healthy
  - Valkey running
  - Worker running

## Current GitHub State

- Repository: https://github.com/Ibra0hh/chessju
- Branch: `main`
- Latest completed Phase 13 commit before Phase 14: `6f75be6871c018aeb64d0fd200e0d066402bed56`
- Git status before Phase 14 implementation: clean

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
- Chess clock clients should send meaningful event snapshots only, not every tick.
- Direct chat is member-only and text-only in Phase 12.
- Message deletion must be soft deletion.
- In-app notification payloads must not contain secrets, raw PGN, or unnecessary message bodies.
- SSE events are lightweight hints; REST endpoints remain authoritative.
- API error responses must use the standard `{ "error": ... }` shape.
- Every response should include `X-Request-ID`.
- CORS origins must be explicit when credentials are enabled.
- Rate limits should protect expensive and abuse-prone endpoints.
- Do not commit secrets.
- Do not commit `.env`.
- Do not use Firebase, Supabase, Appwrite, PocketBase, or any BaaS as the core backend.

## Not Implemented Yet

- Flutter frontend
- Automatic Swiss pairing
- Automatic round-robin generation
- Advanced tie-breaks
- Production monitoring stack
- External object storage
- Push notifications
- Email notifications
- Full WebSocket chat
- Guaranteed distributed event delivery
- Scheduled Chess.com sync
- Realtime clock broadcast
- Player-controlled official tournament clocks
- Clock drift reconciliation or anti-cheat logic
- Group chat
- Tournament chat
- Media messages
- End-to-end encrypted direct messages

## Recommended Next Phase

Recommended next phase should be approved explicitly before work starts.

Candidate next areas:

- Flutter client planning if the backend MVP should be exercised from the future app surface.
- Group or tournament chat if Ibrahim wants to extend social features beyond direct messages.
- Automatic pairing if tournament operations should move beyond manual pairing.
