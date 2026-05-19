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

Phase 3 admin tables:

- `admin_action_logs`

`admin_action_logs` records who performed an admin action, the action name, the entity type and
optional entity ID, sanitized before/after snapshots, request metadata, and creation time.

Phase 4 content tables:

- `files`
- `articles`
- `announcements`

`files` stores metadata for local filesystem-backed uploads. API responses expose safe metadata and
file IDs, not internal storage paths.

`articles` stores draft, published, and archived news. Articles use unique slugs, `published_at`,
and `deleted_at` for soft delete behavior.

`announcements` stores draft, published, and archived club announcements with simple target,
priority, expiration, and soft delete fields. `tournament_id` is nullable and intentionally has no
foreign key until tournaments are implemented.
