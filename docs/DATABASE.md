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

Phase 5 tournament tables:

- `time_controls`
- `tournaments`
- `tournament_registrations`

`time_controls` stores reusable clock definitions such as rapid or blitz controls.

`tournaments` stores the admin-managed tournament shell, including title, unique slug, status,
format, optional time control, capacity, schedule, location, cover file, and soft delete timestamp.

`tournament_registrations` stores each user registration with a unique `(tournament_id, user_id)`
constraint. Registration statuses are `pending`, `approved`, `waitlisted`, `cancelled`, and
`rejected`.
