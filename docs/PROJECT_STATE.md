# ChessJU Project State

Checkpoint date: 2026-05-19

## Project Identity

- Project name: ChessJU
- Owner: Ibrahim
- Purpose: custom chess club platform for University of Jordan members

ChessJU now has a backend MVP foundation and an initial Flutter/Dart app foundation. The Flutter
client is intentionally simple and focused on connecting cleanly to the existing backend.

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
- Flutter/Dart frontend foundation under `frontend/chessju_app`

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

### Phase 15: Flutter App Foundation

- Flutter project under `frontend/chessju_app`
- Android, iOS, Web, and Windows desktop project scaffold
- iOS folder included; iOS build, signing, TestFlight, and App Store release require macOS with Xcode
- Configurable backend base URL
- API client with bearer token and request ID support
- Standard backend error envelope parsing
- Pagination parsing helper
- Secure token storage abstraction
- Riverpod auth/session controller
- Register, login, session check, and logout flow foundation
- GoRouter routing
- ChessJU Material 3 light/dark theme
- Initial screens:
  - Splash
  - Login
  - Register
  - Home
  - News list
  - Tournament list
  - Leaderboard
  - Games placeholder
  - Notifications
  - Profile
- Home screen consumes `GET /api/v1/home`
- News, tournaments, leaderboard, notifications, unread count, and profile screens consume existing
  backend endpoints
- Realtime SSE service placeholder for later UI integration
- Flutter app documentation in `docs/FLUTTER_APP.md`

### Phase 16: Flutter UI Vertical Slice

- Responsive Flutter app shell with compact bottom navigation and wider-screen navigation rail
- Auth UI polish for loading, validation, and backend error messages
- Home screen connected to backend home data
- News list and news detail screens connected to backend news endpoints
- Tournament list and tournament detail screens connected to backend tournament endpoints
- Tournament registration and cancellation actions from Flutter
- Tournament rounds and standings shown on tournament detail
- Leaderboard screen shows season context and ranking rows
- Games screen lists current user's games
- Notifications screen shows unread count, read state, mark-one-read, and mark-all-read actions
- Profile screen shows user/profile/preference data and supports basic profile editing
- Shared loading, error, empty, primary button, status chip, and content row widgets
- Expanded Dart models for article detail, tournament detail, registration, rounds, standings,
  leaderboard, games, notifications, and preferences
- Flutter tests expanded for login validation, model parsing, shared states, and token storage

### Phase 17: Flutter Game Library And Analysis Board UI

- Game library filters for all games, tournament games, PGN uploads, and Chess.com imports
- Game detail screen connected to `GET /api/v1/games/{game_id}`
- Read-only chess board replay from backend FEN data
- First, previous, next, final, and move-list jump controls
- Last-move highlighting from UCI coordinates
- PGN metadata and SAN move list display
- PGN paste screen connected to `POST /api/v1/games/pgn/paste`
- Analysis request action connected to `POST /api/v1/games/{game_id}/analysis`
- Analysis status and report display connected to existing analysis endpoints
- Approximate accuracy, classification counts, selected-move evaluation, centipawn loss, best move,
  and principal variation shown when an analysis report exists
- PGN file upload, engine arrows, evaluation graph, and draggable board input intentionally delayed

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
- Flutter app foundation routes and API client
- Flutter vertical-slice screens consuming backend content/authenticated endpoints
- Flutter game library, PGN paste, game detail, board replay, and analysis report UI

## Current Worker And Queue State

- Worker package exists under `worker/`
- Worker runs as a Docker Compose service
- Valkey/RQ is used for queue transport
- `analysis` queue exists for Stockfish analysis jobs
- `chesscom` queue exists for Chess.com sync jobs
- Stockfish analysis jobs run in the worker
- Chess.com sync jobs run in the worker

## Current Flutter App State

- Flutter project path: `frontend/chessju_app`
- Backend base URL default: `http://localhost:8001`
- Android emulator backend URL: `http://10.0.2.2:8001`
- iOS simulator backend URL on macOS: `http://localhost:8001`
- Physical device backend URL: use the computer LAN IP
- iOS release path: verify/build/sign on macOS with Xcode or macOS CI
- Main packages:
  - `go_router`
  - `dio`
  - `flutter_riverpod`
  - `flutter_secure_storage`
  - `shared_preferences`
  - `uuid`
- Flutter analyze: passed at Phase 17 implementation time
- Flutter test: passed at Phase 17 implementation time
- Current vertical slice consumes:
  - `/api/v1/home`
  - `/api/v1/news`
  - `/api/v1/news/{slug}`
  - `/api/v1/tournaments`
  - `/api/v1/tournaments/{slug}`
  - `/api/v1/tournaments/{tournament_id}/register`
  - `/api/v1/tournaments/{tournament_id}/registration`
  - `/api/v1/tournaments/{slug}/rounds`
  - `/api/v1/tournaments/{slug}/standings`
  - `/api/v1/leaderboard`
  - `/api/v1/leaderboard/seasons`
  - `/api/v1/games`
  - `/api/v1/games/{game_id}`
  - `/api/v1/games/pgn/paste`
  - `/api/v1/games/{game_id}/analysis`
  - `/api/v1/analysis/jobs/{job_id}`
  - `/api/v1/analysis/reports/{report_id}`
  - `/api/v1/notifications`
  - `/api/v1/notifications/unread-count`
  - `/api/v1/notifications/{notification_id}/read`
  - `/api/v1/notifications/read-all`
  - `/api/v1/users/me`
  - `/api/v1/users/me/profile`

## Current Test And Quality Status

Latest known verification at this checkpoint:

- pytest: `306 passed`
- Ruff: passed
- Alembic current head: `0013_realtime_notifications`
- Flutter analyze: passed
- Flutter test: `15 passed`
- Docker stack status:
  - API running on `http://localhost:8001`
  - PostgreSQL running and healthy
  - Valkey running
  - Worker running

## Current GitHub State

- Repository: https://github.com/Ibra0hh/chessju
- Branch: `main`
- Latest completed Phase 16 commit before Phase 17:
  `922c48f5202b9c05a828c9069a5c8786e802bd32`
- Git status before Phase 17 implementation: clean

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
- Flutter must treat backend REST responses as authoritative.
- Flutter must refetch official state after realtime hints.

## Not Implemented Yet

- Full Flutter UI implementation beyond the current vertical slice
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
- Admin dashboard frontend
- Deep-link routing for every detail page
- Full SSE subscription UI
- PGN file upload UI
- Chess.com import UI
- Chess clock UI
- Friends/direct chat UI
- Draggable board input
- Engine arrows
- Evaluation graph

## Recommended Next Phase

Recommended next phase should be approved explicitly before work starts.

Candidate next areas:

- Add Chess.com import, chess clock, or friends/direct chat UI after Ibrahim chooses the next product
  slice.
- Add PGN file upload, engine arrows, and an evaluation graph as later game-review refinements.
- Build a dedicated Flutter admin dashboard when Ibrahim wants admin workflows outside OpenAPI.
- Add automatic pairing if tournament operations should move beyond manual pairing.
