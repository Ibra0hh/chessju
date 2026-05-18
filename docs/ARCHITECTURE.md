# ChessJU Architecture

ChessJU uses a modular monolith.

The backend is a Python FastAPI application backed by PostgreSQL. PostgreSQL is the source of truth for users, tournaments, games, leaderboards, audit logs, and file metadata.

Valkey is reserved for cache, rate limits, queues, temporary realtime state, and later presence. It must not store official business records.

Flutter/Dart clients will consume REST JSON APIs first. SSE will be added for simple server-to-client updates. WebSockets are delayed until chat and live interactive features.
