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
