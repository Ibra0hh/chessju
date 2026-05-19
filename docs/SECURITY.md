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
- A player cannot appear twice in the same active round
- Pairing result submission is admin-only in this phase
- Cancelled pairings cannot receive results
- Public round and pairing endpoints hide draft rounds
- Round, pairing, and result mutations write audit log entries

Phase 6 scoring:

- `white_win`: white +1
- `black_win`: black +1
- `draw`: both +0.5
- `white_forfeit`: black +1
- `black_forfeit`: white +1
- `double_forfeit`: both +0
- `bye`: player +1
