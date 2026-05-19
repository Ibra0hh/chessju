# ChessJU Backend Smoke Tests

These are manual verification flows for local development. Do not paste real secrets into commands
or docs.

## Local Demo Flow

Use this flow when preparing a local release-candidate demo:

1. Start the Docker stack.
2. Run Alembic migrations.
3. Seed local demo data.
4. Run the backend smoke script.
5. Run Flutter web.
6. Login as the demo admin.
7. Login as a demo member.
8. Test tournament registration, rounds, pairings, and standings.
9. Test PGN paste and analysis request/status.
10. Test friends, direct chat, notifications, and unread count.
11. Test the chess clock.

```powershell
docker compose -f infra/docker-compose.dev.yml up --build -d

cd backend
$env:CHESSJU_DATABASE_URL = "postgresql+psycopg://chessju:chessju_dev_password@localhost:5432/chessju"
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\python.exe scripts\seed_demo_data.py --yes --database-url $env:CHESSJU_DATABASE_URL
..\.venv\Scripts\python.exe scripts\smoke_test_api.py `
  --base-url http://localhost:8001 `
  --member-email member4@example.com `
  --member-password ChangeMe123! `
  --friend-email member5@example.com `
  --friend-password ChangeMe123! `
  --admin-email admin@example.com `
  --admin-password ChangeMe123!

cd ..\frontend\chessju_app
flutter run -d chrome --dart-define=CHESSJU_API_BASE_URL=http://localhost:8001
```

The demo credentials above are for local development only:

- Admin: `admin@example.com` / `ChangeMe123!`
- Members: `member1@example.com` through `member5@example.com` / `ChangeMe123!`

Do not use these credentials in production, staging, or any public environment.

## Demo Seed Script

`backend/scripts/seed_demo_data.py` creates repeatable local demo data:

- one admin/super admin account
- five member accounts
- profiles, preferences, and notification preferences
- published news and announcement content
- a rapid time control
- a demo tournament with registrations, rounds, pairings, results, and leaderboard data
- one PGN-upload-style game
- a friendship, direct conversation, and sample messages

Safety rules:

- The script requires `--yes`.
- The script only runs when `CHESSJU_ENVIRONMENT` is `development`, `local`, or `test`.
- The script does not run automatically.
- The script does not create a hidden admin endpoint.
- The script is idempotent for the seeded demo records.

When running from the Windows host against Docker PostgreSQL, pass the localhost database URL shown
above. Inside a Docker container, the normal Docker service hostname can be used through
`CHESSJU_DATABASE_URL`.

## Automated API Smoke Script

`backend/scripts/smoke_test_api.py` verifies a running local API and prints pass/fail results. It
does not print access tokens, refresh tokens, passwords, token hashes, or authorization headers.

The script checks health endpoints, auth, public content, tournament lists, leaderboard, PGN paste,
analysis request creation, clock events, friend request/direct message flow, notification unread
count, and admin identity/audit logs when admin credentials are provided.

Admin sections are skipped when admin credentials are omitted. Existing friend relationships are
handled as a non-failing skip so the script can be run repeatedly against seeded data.

## 1. Health Checks

```powershell
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8001/version
Invoke-RestMethod http://localhost:8001/health/db
Invoke-RestMethod http://localhost:8001/health/valkey
```

Expected: `/health` and `/version` are lightweight. `/health/db` checks PostgreSQL.
`/health/valkey` checks Valkey.

## 2. Register And Login

Use `POST /api/v1/auth/register`, then `POST /api/v1/auth/login`.

Save:

- `access_token`
- `refresh_token`

Authenticated requests need:

```text
Authorization: Bearer <access_token>
```

## 3. Create A Dev Admin

There is no hidden admin creation endpoint. Use one of these local-only methods:

- Run `backend/scripts/seed_demo_data.py` to create `admin@example.com`.
- Register a normal user, then assign the admin role with a manual SQL update against the local
  database.

Example outline:

```sql
insert into user_roles (user_id, role_id)
select '<registered-user-id>'::uuid, id
from roles
where name = 'admin'
on conflict do nothing;
```

Re-login after role assignment so the access token contains the admin role.

## 4. News And Announcements

Admin:

- `POST /api/v1/admin/news`
- `POST /api/v1/admin/news/{article_id}/publish`
- `POST /api/v1/admin/announcements`

Public:

- `GET /api/v1/news`
- `GET /api/v1/announcements`
- `GET /api/v1/home`

## 5. Tournament Flow

Admin:

- create a time control
- create a tournament
- publish it
- open registration

Member:

- `POST /api/v1/tournaments/{tournament_id}/register`

Admin:

- close registration
- create a round
- create manual pairings
- submit a result

Public:

- `GET /api/v1/tournaments/{slug}/rounds`
- `GET /api/v1/tournaments/{slug}/pairings`
- `GET /api/v1/tournaments/{slug}/standings`

## 6. JU Leaderboard

Admin:

- `POST /api/v1/admin/leaderboard/recompute`

Public:

- `GET /api/v1/leaderboard`
- `GET /api/v1/home`

## 7. PGN And Analysis

Member:

- paste PGN with `POST /api/v1/games/pgn/paste`
- check `GET /api/v1/games`
- request analysis with `POST /api/v1/games/{game_id}/analysis`
- check job status with `GET /api/v1/analysis/jobs/{job_id}`
- fetch report with `GET /api/v1/games/{game_id}/analysis`

Analysis runs through the worker and Stockfish, not inside the API request.

## 8. Chess.com Import

Member:

- connect a public username with `POST /api/v1/integrations/chesscom/connect`
- request sync with `POST /api/v1/integrations/chesscom/sync`
- inspect `GET /api/v1/integrations/chesscom/sync-jobs`
- inspect imported games with `GET /api/v1/games?source=chesscom_import`

ChessJU uses only public Chess.com data. Do not enter a Chess.com password.

## 9. Chess Clock

Member:

- create a casual session with `POST /api/v1/clock/sessions`
- start
- switch turn
- pause
- resume
- complete
- fetch events with `GET /api/v1/clock/sessions/{session_id}/events`

The backend stores meaningful snapshots only, not every tick.

## 10. Friends And Direct Chat

Member A:

- send friend request with `POST /api/v1/friends/requests`

Member B:

- accept with `POST /api/v1/friends/requests/{request_id}/accept`

Then:

- create direct conversation with `POST /api/v1/conversations/direct`
- send message with `POST /api/v1/conversations/{conversation_id}/messages`
- list messages with `GET /api/v1/conversations/{conversation_id}/messages`

## 11. Notifications And Unread Count

After friend request or direct message flows:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  http://localhost:8001/api/v1/notifications

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  http://localhost:8001/api/v1/notifications/unread-count
```

## 12. SSE Auth Check

Unauthenticated access should return `401`:

```powershell
Invoke-WebRequest http://localhost:8001/api/v1/realtime/stream
```

Authenticated clients should connect with `Authorization: Bearer <access_token>`. SSE payloads are
hints; refetch REST endpoints for full state.

## 13. Request ID And Error Shape

```powershell
Invoke-WebRequest `
  -Headers @{ "X-Request-ID" = "manual-smoke-1" } `
  http://localhost:8001/api/v1/auth/me
```

Expected:

- response includes `X-Request-ID`
- JSON body uses `{ "error": { "code", "message", "details", "request_id" } }`

## 14. Rate Limit Check

Use a safe local account and repeat login quickly. After the configured threshold, the API should
return:

```json
{
  "error": {
    "code": "rate_limit.exceeded"
  }
}
```

Do not use real credentials for manual stress tests.
