# ChessJU Database

PostgreSQL is the source of truth.

Phase 1 creates migration infrastructure only. Business tables should be added in later phase-specific migrations.

Use UUID primary keys unless there is a strong reason not to. Use foreign keys, unique constraints, and transactions for critical flows.

Phase 2 auth/user tables:

- `users`
- `profiles`
- `roles`
- `user_roles`
- `user_preferences`
- `refresh_tokens`

Phase 3 admin tables:

- `admin_action_logs`

`admin_action_logs` records who performed an admin action, the action name, the entity type and
optional entity ID, sanitized before/after snapshots, request metadata, and creation time.

Phase 4 content tables:

- `files`
- `articles`
- `announcements`

`files` stores metadata for local filesystem-backed uploads. API responses expose safe metadata and
file IDs, not internal storage paths.

`articles` stores draft, published, and archived news. Articles use unique slugs, `published_at`,
and `deleted_at` for soft delete behavior.

`announcements` stores draft, published, and archived club announcements with simple target,
priority, expiration, and soft delete fields. `tournament_id` is nullable and intentionally has no
foreign key until tournaments are implemented.

Phase 5 tournament tables:

- `time_controls`
- `tournaments`
- `tournament_registrations`

`time_controls` stores reusable clock definitions such as rapid or blitz controls.

`tournaments` stores the admin-managed tournament shell, including title, unique slug, status,
format, optional time control, capacity, schedule, location, cover file, and soft delete timestamp.

`tournament_registrations` stores each user registration with a unique `(tournament_id, user_id)`
constraint. Registration statuses are `pending`, `approved`, `waitlisted`, `cancelled`, and
`rejected`.

Phase 6 playing-flow tables:

- `rounds`
- `pairings`
- `games`

`rounds` belongs to a tournament and has a unique `(tournament_id, round_number)` constraint.

`pairings` belongs to both a round and tournament for simpler queries. Board numbers are unique per
round. Pairing results support pending, wins, draws, forfeits, double forfeits, and byes.

`games` is the shared game-library foundation. In this phase, tournament result submission creates
or updates one linked `games` row per pairing. PGN uploads and imported games will reuse this table
later.

Basic tournament standings are computed live from completed pairings and approved registrations.
Tie-break tables are intentionally delayed.

Phase 7 JU leaderboard tables:

- `seasons`
- `player_ratings`
- `rating_events`
- `leaderboard_snapshots`

`seasons` defines named ranking windows. Only one season should be active at a time; this is enforced
by service logic and a PostgreSQL partial unique index for `active = true`.

`player_ratings` stores per-user rating rows. Phase 7 uses `internal` ratings when present and
defaults leaderboard rows to 1200 when no rating row exists. Elo-style updates are not implemented
yet.

`rating_events` is reserved for future rating history. Phase 7 creates the table but does not write
rating events.

`leaderboard_snapshots` stores generated leaderboard rows for all-time rankings (`season_id` null)
or a specific season. Recompute deletes the previous snapshots for that scope and inserts fresh rows
with a shared `generated_at` timestamp.

Phase 7 leaderboard scoring uses completed tournament games/results from non-deleted,
non-cancelled tournaments and approved tournament registrations. Ranking sorts by points, wins,
draws, games played, then username.

Phase 8 PGN and game-library changes:

- `games.owner_id`
- `games.metadata`
- `games.initial_fen`
- `games.final_fen`
- `game_moves`
- `pgn_imports`

`games.owner_id` identifies the user who uploaded/imported a private PGN game. Tournament games keep
using `white_user_id`, `black_user_id`, `pairing_id`, `round_id`, and `tournament_id`.

`games.metadata` stores PGN headers such as Event, Site, Date, Round, White, Black, Result, ECO,
Opening, and TimeControl. `initial_fen` and `final_fen` support Flutter board replay.

`game_moves` stores one normalized row per ply with SAN, UCI, FEN before, FEN after,
check/checkmate flags, comments, side, and move number. Rows are unique by `(game_id, ply_number)`.

`pgn_imports` records paste/file upload imports, status, optional file ID, linked game ID, and
completion time. Phase 8 parses synchronously in the API request; future background imports can reuse
this table.

Phase 9 Stockfish analysis tables:

- `analysis_jobs`
- `analysis_reports`
- `analysis_move_evaluations`

`analysis_jobs` stores queued, running, completed, failed, and cancelled analysis requests. Each job
belongs to a game and requesting user, stores engine/depth settings, and records start/completion
timestamps plus a safe failure message when needed.

`analysis_reports` stores one generated report for an analysis job with summary JSON, approximate
white/black accuracy, final evaluation, and creation time.

`analysis_move_evaluations` stores one row per analyzed game move. Rows include the linked
`game_moves` row, ply number, side, SAN, UCI, evaluation before/after, best move, short principal
variation, centipawn loss, and ChessJU's basic move classification. Rows are unique by
`(analysis_report_id, ply_number)`.

Analysis jobs are created by the API and processed by the worker through Valkey/RQ. Stockfish output
is stored in PostgreSQL; Valkey is only the transient queue transport.
