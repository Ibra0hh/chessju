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
