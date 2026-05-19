# ChessJU API

REST JSON APIs come first.

Phase 1 operational endpoints:

- `GET /health`
- `GET /version`
- `GET /health/db`

Future domain APIs should use clear request and response schemas and should be designed for Flutter/Dart clients.

Phase 2 auth/user endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me/profile`
- `GET /api/v1/users/me/preferences`
- `PATCH /api/v1/users/me/preferences`

Phase 3 admin endpoints:

- `GET /api/v1/admin/me`
- `GET /api/v1/admin/audit-logs`

Admin endpoints require an `admin` or `super_admin` role. Audit logs support `limit`, `offset`,
`action`, `entity_type`, and `admin_id` query parameters and are sorted newest first.

Phase 4 content endpoints:

- `GET /api/v1/home`
- `GET /api/v1/news`
- `GET /api/v1/news/{slug}`
- `GET /api/v1/announcements`
- `POST /api/v1/admin/files`
- `POST /api/v1/admin/news`
- `GET /api/v1/admin/news`
- `GET /api/v1/admin/news/{article_id}`
- `PATCH /api/v1/admin/news/{article_id}`
- `POST /api/v1/admin/news/{article_id}/publish`
- `POST /api/v1/admin/news/{article_id}/archive`
- `DELETE /api/v1/admin/news/{article_id}`
- `POST /api/v1/admin/announcements`
- `GET /api/v1/admin/announcements`
- `PATCH /api/v1/admin/announcements/{announcement_id}`
- `POST /api/v1/admin/announcements/{announcement_id}/publish`
- `POST /api/v1/admin/announcements/{announcement_id}/archive`
- `DELETE /api/v1/admin/announcements/{announcement_id}`

Public news and announcements return only published, non-deleted content. The home endpoint returns
stable Flutter-ready keys: `announcements`, `latest_news`, `upcoming_tournaments`, and
`leaderboard_preview`.

Phase 5 tournament endpoints:

- `GET /api/v1/tournaments`
- `GET /api/v1/tournaments/{slug}`
- `POST /api/v1/tournaments/{tournament_id}/register`
- `DELETE /api/v1/tournaments/{tournament_id}/registration`
- `GET /api/v1/users/me/tournament-registrations`
- `POST /api/v1/admin/time-controls`
- `GET /api/v1/admin/time-controls`
- `PATCH /api/v1/admin/time-controls/{time_control_id}`
- `POST /api/v1/admin/tournaments`
- `GET /api/v1/admin/tournaments`
- `GET /api/v1/admin/tournaments/{tournament_id}`
- `PATCH /api/v1/admin/tournaments/{tournament_id}`
- `POST /api/v1/admin/tournaments/{tournament_id}/publish`
- `POST /api/v1/admin/tournaments/{tournament_id}/open-registration`
- `POST /api/v1/admin/tournaments/{tournament_id}/close-registration`
- `POST /api/v1/admin/tournaments/{tournament_id}/cancel`
- `DELETE /api/v1/admin/tournaments/{tournament_id}`
- `GET /api/v1/admin/tournaments/{tournament_id}/registrations`
- `PATCH /api/v1/admin/tournament-registrations/{registration_id}`

Public tournament lists show non-deleted visible tournaments and support `limit`, `offset`, and
`status`. Registration requires authentication and only works while tournament status is
`registration_open`.

Phase 6 tournament playing-flow endpoints:

- `GET /api/v1/tournaments/{slug}/rounds`
- `GET /api/v1/tournaments/{slug}/rounds/{round_number}`
- `GET /api/v1/tournaments/{slug}/pairings`
- `GET /api/v1/tournaments/{slug}/standings`
- `GET /api/v1/users/me/pairings`
- `POST /api/v1/admin/tournaments/{tournament_id}/rounds`
- `GET /api/v1/admin/tournaments/{tournament_id}/rounds`
- `GET /api/v1/admin/rounds/{round_id}`
- `PATCH /api/v1/admin/rounds/{round_id}`
- `POST /api/v1/admin/rounds/{round_id}/publish`
- `POST /api/v1/admin/rounds/{round_id}/start`
- `POST /api/v1/admin/rounds/{round_id}/complete`
- `POST /api/v1/admin/rounds/{round_id}/cancel`
- `POST /api/v1/admin/rounds/{round_id}/pairings`
- `POST /api/v1/admin/rounds/{round_id}/pairings/bulk`
- `GET /api/v1/admin/rounds/{round_id}/pairings`
- `PATCH /api/v1/admin/pairings/{pairing_id}`
- `DELETE /api/v1/admin/pairings/{pairing_id}`
- `POST /api/v1/admin/pairings/{pairing_id}/result`
- `GET /api/v1/admin/tournaments/{tournament_id}/standings`

Round drafts are admin-only. Public users see published, in-progress, completed, and cancelled
rounds. Pairings are manual in this phase. Standings are computed live from completed pairings.

Phase 7 JU leaderboard endpoints:

- `GET /api/v1/leaderboard`
- `GET /api/v1/leaderboard/seasons`
- `GET /api/v1/leaderboard/seasons/{season_id}`
- `POST /api/v1/admin/leaderboard/seasons`
- `GET /api/v1/admin/leaderboard/seasons`
- `PATCH /api/v1/admin/leaderboard/seasons/{season_id}`
- `POST /api/v1/admin/leaderboard/seasons/{season_id}/activate`
- `POST /api/v1/admin/leaderboard/recompute`
- `GET /api/v1/admin/leaderboard`

The public leaderboard reads from generated snapshots. `GET /api/v1/leaderboard` returns the active
season leaderboard when an active season exists, otherwise it returns all-time snapshots. Admins can
recompute all-time snapshots with `season_id: null` or recompute a specific season by ID.

The home endpoint now fills `leaderboard_preview` from the top five public leaderboard snapshot rows.
If no matching snapshot exists, the preview is an empty list.

Phase 8 PGN game-library endpoints:

- `POST /api/v1/games/pgn/paste`
- `POST /api/v1/games/pgn/upload`
- `GET /api/v1/games`
- `GET /api/v1/games/{game_id}`
- `GET /api/v1/games/{game_id}/moves`
- `GET /api/v1/pgn-imports`
- `GET /api/v1/admin/games`
- `GET /api/v1/admin/pgn-imports`

PGN paste and upload require authentication. The backend parses the first PGN game with
`python-chess`, stores one `games` row, stores ordered `game_moves`, and returns a normalized
analysis-board response with metadata, initial/final FEN, SAN, UCI, FEN before/after, comments, and
check/checkmate flags.

`GET /api/v1/games` returns the current user's uploaded PGN games plus tournament games where the
user is white or black. `GET /api/v1/games/{game_id}` and `/moves` enforce the same object-level
authorization. Admin users can list all games and imports through the admin endpoints.

Phase 8 does not include Stockfish, engine evaluations, best moves, blunder labels, Chess.com
imports, or public game pages.

Phase 9 Stockfish analysis endpoints:

- `POST /api/v1/games/{game_id}/analysis`
- `GET /api/v1/analysis/jobs/{job_id}`
- `GET /api/v1/games/{game_id}/analysis`
- `GET /api/v1/analysis/reports/{report_id}`
- `GET /api/v1/admin/analysis/jobs`
- `GET /api/v1/admin/analysis/reports`

Analysis requests require authentication and the same object-level game access used by the game
library. The API creates an `analysis_jobs` row, enqueues a Valkey/RQ job, and returns job status.
The worker runs Stockfish outside the request/response cycle and stores one report with ordered move
evaluations.

`POST /api/v1/games/{game_id}/analysis` accepts an optional `depth`. If a queued/running job already
exists for the same user, game, and depth, the existing job is returned. If a completed report already
exists for the same game and depth, the completed job is returned instead of creating duplicate work.

Analysis report responses include approximate accuracy, a summary count by side, final evaluation,
and one row per move with evaluation before/after, best move, short principal variation, centipawn
loss, and a simple ChessJU classification. They intentionally do not copy Chess.com Game Review
branding, wording, or proprietary behavior.

The response shape is also meant to support later Flutter UI elements such as an evaluation bar,
evaluation graph, best-move display, principal variation, move coloring, and an accuracy summary.
Those UI features are not implemented in Phase 9.

Chesskit may be considered only as a conceptual reference for common chess-review ideas. Do not copy
Chesskit code, UI layout, assets, names, branding, or exact wording into ChessJU.

Phase 10 Chess.com public import endpoints:

- `POST /api/v1/integrations/chesscom/connect`
- `GET /api/v1/integrations/chesscom/account`
- `DELETE /api/v1/integrations/chesscom/account`
- `POST /api/v1/integrations/chesscom/sync`
- `GET /api/v1/integrations/chesscom/sync-jobs`
- `GET /api/v1/integrations/chesscom/sync-jobs/{job_id}`
- `GET /api/v1/integrations/chesscom/imported-games`
- `GET /api/v1/admin/chesscom/accounts`
- `GET /api/v1/admin/chesscom/sync-jobs`
- `GET /api/v1/admin/chesscom/imported-games`

Users connect one Chess.com username using public profile data only. ChessJU never asks for or
stores Chess.com passwords. Sync requests create `chesscom_sync_jobs` rows and enqueue background
worker work through Valkey/RQ. The worker fetches public monthly archives serially, imports valid
PGNs into the shared `games` and `game_moves` tables, creates `pgn_imports` with source
`chesscom`, and records import metadata in `chesscom_imported_games`.

Imported Chess.com games appear in `GET /api/v1/games?source=chesscom_import` and can use the
existing analysis endpoints. Sync tests mock Chess.com responses; the test suite does not depend on
live network access.

Phase 11 chess clock endpoints:

- `POST /api/v1/clock/sessions`
- `GET /api/v1/clock/sessions/{session_id}`
- `GET /api/v1/clock/sessions/{session_id}/events`
- `POST /api/v1/clock/sessions/{session_id}/start`
- `POST /api/v1/clock/sessions/{session_id}/pause`
- `POST /api/v1/clock/sessions/{session_id}/resume`
- `POST /api/v1/clock/sessions/{session_id}/switch-turn`
- `POST /api/v1/clock/sessions/{session_id}/adjust`
- `POST /api/v1/clock/sessions/{session_id}/flag`
- `POST /api/v1/clock/sessions/{session_id}/complete`
- `POST /api/v1/clock/sessions/{session_id}/reset`
- `POST /api/v1/clock/sessions/{session_id}/cancel`
- `GET /api/v1/admin/clock/sessions`
- `GET /api/v1/admin/clock/sessions/{session_id}`
- `GET /api/v1/admin/clock/sessions/{session_id}/events`

Chess clock sessions can be casual or linked to tournament pairings. Casual sessions are controlled
by the creator. Pairing-linked official sessions are created and controlled by admins or super
admins, while the paired players can view the session and event log.

The clock runs on the Flutter client for responsiveness. The backend stores only meaningful
snapshots: setup, start, pause, resume, switch turn, adjust time, flag, reset, complete, and cancel.
It does not receive every second or tick.

Clock event logs are append-only and returned oldest first. Mutation responses return the updated
clock session with remaining time, active color, status, result, and timestamps.
