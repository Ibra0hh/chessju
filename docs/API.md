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
