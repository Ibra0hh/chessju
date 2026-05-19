# ChessJU Security

Never commit secrets.

Use environment variables for database URLs, JWT secrets, passwords, and API keys.

MVP authentication will use custom JWT auth with short-lived access tokens and hashed refresh tokens. Every admin mutation must create an audit log.

Phase 2 auth foundation uses:

- Argon2id password hashing
- JWT access tokens
- hashed refresh tokens
- refresh token rotation
- default `member`, `arbiter`, `admin`, and `super_admin` roles

Phase 3 admin audit rules:

- Admin endpoints require `admin` or `super_admin`
- Future admin mutations must create an audit log
- Audit logs must never store passwords, password hashes, refresh tokens, token hashes, JWTs, API
  keys, authorization headers, or secrets
- Audit payloads are sanitized before storage

Phase 4 file and content rules:

- Admin file upload requires `admin` or `super_admin`
- Uploaded files are stored on the local filesystem and metadata is stored in PostgreSQL
- Client filenames are not trusted for storage names
- Uploads are checked by declared content type and extension
- Executable extensions are rejected
- File metadata responses do not expose internal absolute filesystem paths
- Article and announcement admin mutations create audit log entries with sanitized before/after data

Phase 5 tournament security rules:

- Tournament creation and lifecycle mutations require `admin` or `super_admin`
- Registration requires an authenticated active user
- Duplicate tournament registration is blocked by service checks and a database unique constraint
- Capacity checks run inside the database transaction and lock the tournament row before counting
  approved registrations
- Admin tournament, time-control, and registration mutations write audit log entries
- Public tournament endpoints hide draft and soft-deleted tournaments

Phase 6 playing-flow security rules:

- Round, pairing, and result admin endpoints require `admin` or `super_admin`
- Manual pairings require approved tournament registrants
- Automatic pairing generation requires `admin` or `super_admin`
- Generated pairings are built from approved tournament registrants only
- Pairing generation rejects cancelled, completed, deleted, or invalid tournament/round states
- Existing pairings are not overwritten unless the admin explicitly requests overwrite and all
  existing results are still pending
- A player cannot appear twice in the same active round
- Pairing result submission is admin-only in this phase
- Cancelled pairings cannot receive results
- Public round and pairing endpoints hide draft rounds
- Round, pairing, generated pairing, and result mutations write audit log entries

Phase 21 automatic pairing limitations:

- Swiss pairing is a simplified ChessJU implementation, not a FIDE-certified pairing engine
- Round-robin generation handles one selected round at a time
- Rematches and color imbalance are avoided where practical, but complex edge cases can still
  require admin review
- Admins can manually edit generated pairings before submitting results

Phase 6 scoring:

- `white_win`: white +1
- `black_win`: black +1
- `draw`: both +0.5
- `white_forfeit`: black +1
- `black_forfeit`: white +1
- `double_forfeit`: both +0
- `bye`: player +1

Phase 7 JU leaderboard security rules:

- Season management and leaderboard recompute require `admin` or `super_admin`
- Public leaderboard endpoints read generated snapshots only
- Recompute uses completed tournament game records and approved tournament registrations
- Activating a season deactivates all other seasons in the same transaction
- Season and recompute admin mutations write audit log entries
- Leaderboard does not expose private auth fields, token data, or internal audit payloads

Not implemented yet:

- Elo updates
- Buchholz
- Sonneborn-Berger
- advanced tie-breaks

Phase 8 PGN and game-library security rules:

- PGN paste and upload require authentication
- PGN paste is limited to 200 KB
- PGN file upload is limited to 5 MB
- PGN upload allows `.pgn` and `.txt` with safe text/PGN/octet-stream MIME handling
- Executable and suspicious upload extensions are rejected
- Client filenames are sanitized and are not trusted for storage paths
- Uploaded file responses and game responses do not expose internal storage paths
- Users can view their own uploaded PGN games
- Users can view tournament games where they are white or black
- Admin and super admin users can view all games and PGN import records
- PGN text is not written to audit logs

Phase 8 analysis-board boundary:

- Backend provides metadata, initial/final FEN, SAN, UCI, FEN before/after, comments, and
  check/checkmate flags
- Basic Stockfish-backed evaluation is implemented in Phase 9; richer review UX and advanced
  engine behavior are still later work

Phase 9 Stockfish analysis security rules:

- Analysis requests require authentication
- Users can request and view analysis only for games they are allowed to view
- Admin and super admin users can view all analysis jobs and reports
- Users cannot analyze another user's private uploaded PGN game
- The API only enqueues analysis jobs; Stockfish does not run inside normal API request handlers
- Failed jobs store safe error messages, not stack traces or secrets
- Analysis limits are controlled by environment settings for depth, maximum plies, and job timeout
- Analysis endpoints should be rate-limited in a later hardening phase

Phase 9 analysis output is approximate:

- Move classification is a simple ChessJU centipawn-loss model
- Accuracy is an approximate internal estimate
- The feature does not copy Chess.com Game Review branding, wording, assets, or proprietary behavior
- Chesskit is allowed only as a conceptual reference; do not copy its AGPL-3.0 source code, UI,
  assets, names, branding, exact wording, files, or implementation details into ChessJU

Not implemented yet:

- Chess.com sync
- cloud-scale engine execution
- exact Game Review clone behavior

Phase 10 Chess.com import security rules:

- ChessJU uses only Chess.com's public, read-only Published Data API
- Users are never asked for Chess.com passwords
- ChessJU does not store Chess.com credentials, tokens, or private API secrets
- The integration does not scrape Chess.com pages
- Username connection stores public profile metadata only
- Sync jobs run in the worker, not inside normal API request handlers
- Sync fetches are capped by `CHESSJU_CHESSCOM_SYNC_MAX_MONTHS`
- Requests use timeouts and a recognizable `CHESSJU_CHESSCOM_USER_AGENT`
- Tests mock Chess.com HTTP responses and do not depend on live public API access
- Users can manage only their own Chess.com account, sync jobs, and imported games
- Admin and super admin users can list integration records for support/operations
- Imported PGN content is parsed through the existing PGN pipeline and is not written to audit logs

Not implemented yet:

- Lichess import
- automatic scheduled Chess.com sync
- auto-analysis after import
- frontend integration UI

Phase 11 chess clock security rules:

- Chess clock endpoints require authentication
- Casual clock sessions can be viewed and controlled by their creator
- Admin and super admin users can view and control every clock session
- Pairing-linked official sessions can be created and controlled only by admins or super admins
- Pairing players can view their official pairing clock session and event log
- Non-player members cannot view official pairing-linked clock sessions
- A pairing cannot have more than one active setup/running/paused clock session
- The backend stores meaningful event snapshots only and must not receive every clock tick
- Clock event logs are append-only; old events are not edited
- Client-provided remaining times are validated as non-negative snapshots, not treated as secrets

Not implemented yet:

- Realtime clock broadcast
- player-controlled official tournament clocks
- clock anti-cheat or drift reconciliation

Phase 12 friends and direct chat security rules:

- Friend, block, conversation, and message endpoints require authentication
- Users cannot send friend requests to themselves
- Users cannot block themselves
- Friend requests are rejected when either user has blocked the other
- Direct conversations require an existing friendship
- Direct conversations are blocked when either user has blocked the other
- Only conversation members can list, view, read, or send messages
- Message bodies are text-only and limited to 2000 characters
- Message deletion is soft deletion through `deleted_at`
- Deleted messages do not expose body content in normal user responses
- Admin and super admin users can list social/chat records for moderation
- Admin deletion of another user's message writes `message.admin_deleted` to the audit log

Not implemented yet:

- group chat
- tournament chat
- media messages
- push notifications
- full realtime chat delivery
- end-to-end encryption

Phase 13 realtime and notification security rules:

- Notification endpoints require authentication
- Users can list, read, and update only their own notifications and notification preferences
- Admin and super admin users can list notifications and realtime events for support/moderation
- User-targeted SSE streams return only events owned by the authenticated user
- SSE payloads are lightweight hints; clients must refetch authoritative state from REST endpoints
- Notification data is sanitized before storage
- Notification data must never include passwords, password hashes, refresh tokens, token hashes,
  JWTs, authorization headers, API keys, secrets, raw PGN, or unnecessary message body content
- Message notifications include safe IDs such as `conversation_id` and `message_id`, not the message
  body
- Notification failures should not break the primary business action unless the transaction itself
  fails

Not implemented yet:

- mobile push notifications
- email notifications
- full WebSocket chat
- group chat realtime
- tournament chat realtime
- guaranteed distributed event delivery

Phase 14 backend hardening rules:

- Common API errors return `{ "error": { "code", "message", "details", "request_id" } }`
- Error responses include `X-Request-ID` and do not expose stack traces, token values, password
  hashes, token hashes, API keys, raw PGN, or internal filesystem paths
- Request ID middleware accepts safe incoming `X-Request-ID` values or generates a UUID
- CORS origins are environment-configured and should remain explicit when credentials are enabled
- Do not configure wildcard CORS origins with credentials in production
- Valkey-backed rate limiting protects login, register, PGN import, analysis request, Chess.com
  sync request, and direct message send paths
- Rate-limit keys are IP-based for unauthenticated auth endpoints and user-based for authenticated
  expensive or abuse-prone endpoints
- `/health` is process liveness and does not depend on PostgreSQL or Valkey
- `/health/db` checks PostgreSQL readiness
- `/health/valkey` checks Valkey readiness
- OpenAPI tags are organized by backend domain for easier Flutter integration

Phase 22 release-candidate QA tooling rules:

- Demo seeding is explicitly local/dev/test only and refuses production environments
- Demo seeding requires an explicit `--yes` confirmation
- Demo users use obvious local-only credentials and must not be used in production or public
  environments
- ChessJU does not expose a hidden admin creation endpoint
- Local admin bootstrapping should happen through the dev seed script or a documented local SQL role
  assignment
- API smoke tooling must not print access tokens, refresh tokens, passwords, password hashes, token
  hashes, or authorization headers
- Smoke tests should use mocked or skipped behavior for external services rather than depending on
  live Chess.com network access

Security review notes:

- `.env` remains ignored and must not be committed
- Public endpoints continue to hide draft, deleted, private, or unauthorized records
- Admin endpoints continue to require `admin` or `super_admin`
- Object-level authorization remains enforced for user-owned games, sync jobs, notifications,
  conversations, clock sessions, and analysis reports
