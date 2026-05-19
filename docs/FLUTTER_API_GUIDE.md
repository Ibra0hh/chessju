# ChessJU Flutter API Guide

This guide describes the backend contract Flutter clients should target. No Flutter code exists in
this repository yet.

## Local Base URL

Local Docker development exposes the API at:

```text
http://localhost:8001
```

All product APIs use:

```text
http://localhost:8001/api/v1
```

## Auth Flow

1. Register with `POST /api/v1/auth/register`.
2. Login with `POST /api/v1/auth/login`.
3. Store the short-lived `access_token` for API calls.
4. Store the `refresh_token` securely and use `POST /api/v1/auth/refresh` to rotate it.
5. Logout with `POST /api/v1/auth/logout` to revoke a refresh token.

The backend uses custom JWT auth. Access tokens are short-lived. Refresh tokens are stored hashed in
PostgreSQL and are rotated on refresh.

## Headers

Authenticated requests:

```text
Authorization: Bearer <access_token>
```

Optional request correlation:

```text
X-Request-ID: <client-generated-safe-id>
```

Every response includes `X-Request-ID`.

## Error Responses

Common errors use this shape:

```json
{
  "error": {
    "code": "auth.unauthorized",
    "message": "Authentication required",
    "details": {},
    "request_id": "uuid-or-client-request-id"
  }
}
```

Common codes include:

- `auth.unauthorized`
- `auth.forbidden`
- `validation.invalid_input`
- `resource.not_found`
- `resource.conflict`
- `rate_limit.exceeded`
- `service.unavailable`
- `server.internal_error`

## Pagination

Most current list endpoints use the established ChessJU shape:

```json
{
  "items": [],
  "limit": 20,
  "offset": 0,
  "total": 0
}
```

Use `limit` and `offset` query parameters. Most endpoints cap `limit` at `100` and reject negative
offsets.

Future endpoints may move toward:

```json
{
  "items": [],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "count": 20
  }
}
```

## Main Endpoint Groups

- Home: `GET /api/v1/home`
- News: `GET /api/v1/news`, `GET /api/v1/news/{slug}`
- Announcements: `GET /api/v1/announcements`
- Tournaments: `GET /api/v1/tournaments`, `GET /api/v1/tournaments/{slug}`
- Registration: `POST /api/v1/tournaments/{id}/register`
- Rounds/pairings/standings:
  - `GET /api/v1/tournaments/{slug}/rounds`
  - `GET /api/v1/tournaments/{slug}/pairings`
  - `GET /api/v1/tournaments/{slug}/standings`
- Leaderboard: `GET /api/v1/leaderboard`
- Games/PGN:
  - `POST /api/v1/games/pgn/paste`
  - `POST /api/v1/games/pgn/upload`
  - `GET /api/v1/games`
  - `GET /api/v1/games/{id}`
- Analysis:
  - `POST /api/v1/games/{id}/analysis`
  - `GET /api/v1/games/{id}/analysis`
  - `GET /api/v1/analysis/jobs/{id}`
  - `GET /api/v1/analysis/reports/{id}`
- Chess.com import:
  - `POST /api/v1/integrations/chesscom/connect`
  - `POST /api/v1/integrations/chesscom/sync`
  - `GET /api/v1/integrations/chesscom/imported-games`
- Clock:
  - `POST /api/v1/clock/sessions`
  - `GET /api/v1/clock/sessions/{id}`
  - `GET /api/v1/clock/sessions/{id}/events`
- Friends/chat:
  - `POST /api/v1/friends/requests`
  - `GET /api/v1/friends`
  - `POST /api/v1/conversations/direct`
  - `POST /api/v1/conversations/{id}/messages`
- Notifications:
  - `GET /api/v1/notifications`
  - `GET /api/v1/notifications/unread-count`
  - `GET /api/v1/notifications/preferences`
- Realtime SSE: `GET /api/v1/realtime/stream`

## SSE Usage

Connect to:

```text
GET /api/v1/realtime/stream
```

The stream requires `Authorization: Bearer <access_token>`.

SSE events are lightweight hints. After receiving important events such as `message.received`,
`analysis.completed`, `chesscom.sync_completed`, or `announcement.published`, the Flutter client
should refetch the relevant REST endpoint for authoritative state.

## Local Development Notes

- API: `http://localhost:8001`
- PostgreSQL and Valkey run inside Docker Compose.
- Docker services use internal hostnames `postgres` and `valkey`.
- Host-side Alembic commands should use a host database URL such as
  `postgresql+psycopg://chessju:chessju_dev_password@localhost:5432/chessju`.
- OpenAPI docs are available at `http://localhost:8001/docs`.
