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
- Stockfish, engine evaluation, candidate lines, best moves, accuracy, and blunder labels are not
  implemented yet
