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
