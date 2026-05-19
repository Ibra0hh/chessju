# ChessJU Project State

Checkpoint date: 2026-05-19

## Project Identity

- Project name: ChessJU
- Owner: Ibrahim
- Purpose: custom chess club platform for University of Jordan members

ChessJU now has a backend MVP foundation, a Flutter/Dart app foundation, release-candidate QA
tooling, and production-style deployment preparation. The Flutter client is intentionally practical
and focused on connecting cleanly to the existing backend.

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

### Phase 18: Flutter Chess Clock UI

- Clock screen available at `/clock`
- Clock route exposed through a timer action in the authenticated app bar
- Casual clock setup with presets:
  - `1 + 0`
  - `1 + 1`
  - `3 + 0`
  - `3 + 2`
  - `5 + 0`
  - `5 + 3`
  - `10 + 0`
  - `15 + 10`
  - custom base/increment
- Responsive two-player timer panels with active, inactive, and warning visual states
- Client-side countdown for responsive tapping
- Backend calls only for meaningful events, not every tick
- Start, pause, resume, switch turn, adjust, flag, complete, reset, and cancel actions
- Switch-turn applies increment locally before sending the event snapshot
- Event history panel reads stored backend clock events
- Simple local UI settings for clock color theme, sound placeholder, and fullscreen placeholder
- Official tournament/pairing clock backend exists, but a dedicated official Flutter flow is not
  implemented yet

### Phase 19: Flutter Friends And Direct Chat UI

- Friends screen available at `/friends`
- Friend requests screen available at `/friend-requests`
- Blocks screen available at `/blocks`
- Conversations list available at `/conversations`
- Direct conversation detail available at `/conversations/{conversationId}`
- Friends route exposed through a People action in the authenticated app bar
- Friend requests can be sent by receiver user ID for development/testing
- Incoming friend requests can be accepted or rejected
- Outgoing pending friend requests can be cancelled
- Friends can be listed, removed, blocked, or opened as direct conversations
- Blocked users can be listed and unblocked
- Conversations list shows direct conversations and last-message summaries
- Message thread supports text send, refresh, best-effort read marking, and soft-delete for own
  messages
- Message UI sanitizes deleted messages
- User search, group chat, tournament chat, media messages, push notifications, and SSE-driven chat
  refresh are intentionally delayed

### Phase 20: Flutter Admin Dashboard And Tournament Manager UI

- Admin dashboard route available at `/admin`
- Admin entry is visible only to users with `admin` or `super_admin` roles
- Admin routes verify access with `/api/v1/admin/me`
- Non-admin users see a forbidden state on manual admin navigation
- Admin dashboard uses wide sidebar navigation and compact section picker navigation
- Admin news screen supports create, edit, publish, archive, and delete
- Admin announcements screen supports create, edit, publish, archive, and delete
- Admin time controls screen supports list, create, and edit
- Admin tournaments screen supports create and list
- Admin tournament detail supports edit, publish, open registration, close registration, cancel, and
  soft delete
- Tournament registration management supports status updates
- Rounds panel supports create and status actions
- Pairings panel supports manual pairing creation, pairing cancellation, and result submission
- Tournament standings are visible from the admin tournament detail
- Admin leaderboard screen supports season creation, activation, recompute, and row viewing
- Admin audit logs screen shows recent admin mutation logs
- Optional read-only admin list panels show games, analysis jobs, Chess.com sync jobs, and
  notifications
- Admin forms use raw user/player IDs where search or picker endpoints do not exist yet
- Rich markdown editor, drag/drop pairings, and production admin polish are intentionally delayed

### Phase 21: Automatic Tournament Pairing Engine

- Admin endpoint for automatic pairing generation:
  `POST /api/v1/admin/rounds/{round_id}/pairings/generate`
- Supported methods:
  - `swiss`
  - `round_robin`
- Basic Swiss generator uses current standings, pairs players with similar scores, avoids rematches
  when practical, assigns byes, and performs simple color balancing
- Round-robin generator uses a circle-style rotation for the selected round, supports odd-player
  byes, and avoids already-played matchups where practical
- Generated pairings are normal `pairings` rows and remain manually editable before results
- Bye pairings are created as completed `bye` results and create tournament game records
- Existing pending pairings can be overwritten only with explicit admin confirmation
- Pairings with submitted results cannot be overwritten by generation
- `pairing.generated` audit log action records the generated pairings
- Flutter admin tournament manager includes a Generate Pairings button, method dropdown, and
  overwrite control
- The pairing engine is practical ChessJU logic and is not FIDE-certified

### Phase 22: End-To-End QA, Demo Data, And Release-Candidate Cleanup

- Local-only demo seed script under `backend/scripts/seed_demo_data.py`
- Demo seed creates:
  - one admin/super admin account
  - five member accounts
  - profiles, preferences, and notification preferences
  - news and announcement demo content
  - time control data
  - a demo tournament with registrations, rounds, pairings, results, and leaderboard data
  - one PGN-upload-style game
  - a friendship, direct conversation, and sample messages
- Demo seed refuses production environments and requires explicit `--yes`
- Local demo credentials are documented as development-only:
  - `admin@example.com` / `ChangeMe123!`
  - `member1@example.com` through `member5@example.com` / `ChangeMe123!`
- Local API smoke script under `backend/scripts/smoke_test_api.py`
- Smoke script checks health, auth, public content, leaderboard, PGN paste, analysis request,
  clock events, friend/direct-message flow, notifications, and admin identity/audit logs when admin
  credentials are provided
- Smoke script redacts tokens, passwords, token hashes, and authorization headers
- Smoke script supports seeded demo credentials and can be rerun against existing friend data
- Documentation now includes a local demo flow from Docker startup through Flutter web manual QA
- No production deployment, external object storage, push notifications, or architecture changes
  were added in this phase

### Phase 23: Production Deployment Foundation

- Production-style compose file under `infra/docker-compose.prod.yml`
- Caddy reverse proxy config under `infra/Caddyfile`
- Safe production environment template under `.env.production.example`
- Production compose includes Caddy, API, worker, PostgreSQL, and Valkey
- Caddy is the only public HTTP/HTTPS entrypoint in production compose
- API, PostgreSQL, and Valkey do not publish public ports in production compose
- Named Docker volumes are used for Postgres, Valkey, local storage, and Caddy state
- PowerShell and POSIX shell backup/restore scripts exist under `infra/backup/`
- Restore scripts require explicit confirmation flags
- Deployment, backup/restore, and production checklist docs were added
- Flutter web deployment is documented as build-only preparation with compile-time API base URL
- No real server deployment was performed
- No external object storage or push notifications were added

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
- Admin automatic pairing generation endpoint
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
- Flutter chess clock UI for casual clock sessions and backend event history
- Flutter friends, blocks, conversations, and direct text message UI
- Flutter admin dashboard, tournament manager, leaderboard recompute, and audit log UI
- Flutter admin automatic pairing controls
- Local demo seed and API smoke-test scripts for release-candidate QA
- Production compose, Caddy, environment template, backup/restore scripts, deployment docs, and
  production checklist

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
- Flutter analyze: passed at Phase 22 verification time
- Flutter test: passed at Phase 22 verification time
- Release-candidate backend smoke script can verify seeded API flows before Flutter manual testing
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
  - `/api/v1/clock/sessions`
  - `/api/v1/clock/sessions/{session_id}/events`
  - `/api/v1/clock/sessions/{session_id}/start`
  - `/api/v1/clock/sessions/{session_id}/pause`
  - `/api/v1/clock/sessions/{session_id}/resume`
  - `/api/v1/clock/sessions/{session_id}/switch-turn`
  - `/api/v1/clock/sessions/{session_id}/adjust`
  - `/api/v1/clock/sessions/{session_id}/flag`
  - `/api/v1/clock/sessions/{session_id}/complete`
  - `/api/v1/clock/sessions/{session_id}/reset`
  - `/api/v1/clock/sessions/{session_id}/cancel`
  - `/api/v1/friends/requests`
  - `/api/v1/friends/requests/{request_id}/accept`
  - `/api/v1/friends/requests/{request_id}/reject`
  - `/api/v1/friends/requests/{request_id}/cancel`
  - `/api/v1/friends`
  - `/api/v1/friends/{user_id}`
  - `/api/v1/blocks`
  - `/api/v1/blocks/{blocked_id}`
  - `/api/v1/conversations`
  - `/api/v1/conversations/direct`
  - `/api/v1/conversations/{conversation_id}`
  - `/api/v1/conversations/{conversation_id}/messages`
  - `/api/v1/conversations/{conversation_id}/read`
  - `/api/v1/messages/{message_id}`
  - `/api/v1/notifications`
  - `/api/v1/notifications/unread-count`
  - `/api/v1/notifications/{notification_id}/read`
  - `/api/v1/notifications/read-all`
  - `/api/v1/users/me`
  - `/api/v1/users/me/profile`
  - `/api/v1/admin/me`
  - `/api/v1/admin/news`
  - `/api/v1/admin/news/{article_id}`
  - `/api/v1/admin/news/{article_id}/publish`
  - `/api/v1/admin/news/{article_id}/archive`
  - `/api/v1/admin/announcements`
  - `/api/v1/admin/announcements/{announcement_id}`
  - `/api/v1/admin/time-controls`
  - `/api/v1/admin/tournaments`
  - `/api/v1/admin/tournaments/{tournament_id}`
  - `/api/v1/admin/tournaments/{tournament_id}/registrations`
  - `/api/v1/admin/tournament-registrations/{registration_id}`
  - `/api/v1/admin/tournaments/{tournament_id}/rounds`
  - `/api/v1/admin/rounds/{round_id}/pairings`
  - `/api/v1/admin/rounds/{round_id}/pairings/generate`
  - `/api/v1/admin/pairings/{pairing_id}/result`
  - `/api/v1/admin/tournaments/{tournament_id}/standings`
  - `/api/v1/admin/leaderboard`
  - `/api/v1/admin/leaderboard/seasons`
  - `/api/v1/admin/leaderboard/recompute`
  - `/api/v1/admin/audit-logs`

## Current Test And Quality Status

Latest known verification at this checkpoint:

- pytest: `322 passed`
- Ruff: passed
- Alembic current head: `0013_realtime_notifications`
- Flutter analyze: passed
- Flutter test: `31 passed`
- Docker stack status:
  - API running on `http://localhost:8001`
  - PostgreSQL running and healthy
  - Valkey running
  - Worker running

## Current GitHub State

- Repository: https://github.com/Ibra0hh/chessju
- Branch: `main`
- Latest completed Phase 22 commit before Phase 23:
  `6e161499bcb68731fd97f4a970b89ad66e7a1410`
- Git status before Phase 23 implementation: clean

## Important Permanent Rules

- PostgreSQL is the source of truth.
- Valkey is not the source of truth.
- Valkey may be used for cache, queues, rate limits, presence later, and temporary state only.
- Admin mutations must write audit logs.
- The frontend must not calculate official tournament standings.
- The frontend must not calculate official JU leaderboard ranks.
- Automatic pairing generation is admin-only and generated pairings must remain auditable.
- Generated pairings are helper output, not final authority; admins can manually review and edit
  pending pairings.
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
- Do not commit `.env.production`.
- Do not commit backup files or database dumps.
- Demo seed credentials are local-only and must never be treated as production credentials.
- Demo seeding must remain explicit and dev-only.
- Caddy is the only public HTTP/HTTPS entrypoint in production compose.
- API, PostgreSQL, and Valkey stay internal-only in production compose.
- Do not use Firebase, Supabase, Appwrite, PocketBase, or any BaaS as the core backend.
- Flutter must treat backend REST responses as authoritative.
- Flutter must refetch official state after realtime hints.

## Not Implemented Yet

- Full Flutter UI implementation beyond the current vertical slice
- Advanced tie-breaks
- Real server production deployment
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
- Dedicated Flutter official tournament/pairing clock flow
- Flutter clock sound/vibration/fullscreen implementation
- Flutter clock offline mode
- Group chat
- Tournament chat
- Media messages
- End-to-end encrypted direct messages
- Flutter user search/discovery for friend requests
- Flutter SSE-driven chat refresh
- Admin rich markdown editor
- Admin user search/player picker
- Admin drag/drop pairing UI
- FIDE-certified tournament pairing
- Advanced color history optimization
- Deep-link routing for every detail page
- Full SSE subscription UI
- PGN file upload UI
- Chess.com import UI
- Draggable board input
- Engine arrows
- Evaluation graph

## Recommended Next Phase

Recommended next phase should be approved explicitly before work starts.

Candidate next areas:

- Production deployment preparation, only after Ibrahim approves moving beyond release-candidate QA.
- Add Chess.com import UI, PGN file upload UI, admin UI polish, or SSE-driven social refresh after
  Ibrahim chooses the next product slice.
- Add PGN file upload, engine arrows, and an evaluation graph as later game-review refinements.
- Add advanced pairing certification and deeper color-history/tie-break logic only if tournament
  operations require it later.
