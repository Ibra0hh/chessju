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
