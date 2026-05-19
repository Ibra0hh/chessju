# ChessJU Flutter App

The Flutter app lives in:

```text
frontend/chessju_app
```

It is part of the ChessJU monorepo. Do not initialize a second Git repository inside the Flutter
folder.

## Local Backend URL

The app reads its API base URL from a Dart define:

```powershell
flutter run --dart-define=CHESSJU_API_BASE_URL=http://localhost:8001
```

Defaults:

- Web/Desktop: `http://localhost:8001`
- Android emulator: `http://10.0.2.2:8001`
- iOS simulator on macOS: `http://localhost:8001`
- Physical devices: use the computer LAN IP, for example `http://192.168.1.25:8001`

Android example:

```powershell
flutter run -d emulator --dart-define=CHESSJU_API_BASE_URL=http://10.0.2.2:8001
```

iOS simulator example on macOS:

```zsh
flutter run -d ios --dart-define=CHESSJU_API_BASE_URL=http://localhost:8001
```

## Run The App

From the Flutter project directory:

```powershell
cd frontend/chessju_app
flutter pub get
flutter run -d chrome --dart-define=CHESSJU_API_BASE_URL=http://localhost:8001
```

## Checks

```powershell
cd frontend/chessju_app
flutter analyze
flutter test
flutter build web
```

The `ios/` folder is included in the project scaffold. iOS builds, signing, TestFlight, and App
Store release require macOS with Xcode. Do not try to build or sign iOS from Windows. Windows
development can still cover most app logic, API integration, routing, state management, tests, web
builds, and Windows desktop builds. Use a Mac or macOS CI when ChessJU is ready for iOS release
verification.

## Current App Foundation

Implemented in Phases 15-20:

- Flutter project scaffold for Android, iOS, Web, and Windows desktop
- iOS project files are included, but iOS build/signing/release must be verified on macOS with Xcode
- Material 3 light/dark ChessJU theme
- `go_router` routing
- `flutter_riverpod` state management
- `dio` API client
- `flutter_secure_storage` token storage abstraction
- Backend error envelope parsing
- Request ID header support
- Pagination parsing helper
- Auth session controller
- Login/register/logout flow foundation
- Splash/session check screen
- Responsive app shell with bottom navigation on compact screens and navigation rail on wider screens
- Home, news, tournaments, leaderboard, games, notifications, and profile screens
- News detail screen
- Tournament detail screen with registration/cancellation actions
- Tournament rounds and standings sections
- Notification read/read-all actions
- Profile edit dialog for full name, University ID, and Chess.com username
- Game library filters for all, tournament, PGN, and Chess.com imported games
- Game detail screen with read-only board replay from FEN
- Move navigation controls and selectable SAN move list
- PGN paste import screen
- Analysis request/status/report UI for existing Stockfish analysis endpoints
- Basic move classification, centipawn loss, best move, and evaluation display
- Chess clock screen available at `/clock`
- Casual clock setup with presets and custom base/increment fields
- Client-side countdown with backend event snapshots for meaningful actions only
- Start, pause, resume, switch-turn, flag, complete, reset, cancel, and adjust-time actions
- Clock event history panel
- Clock visual settings placeholders for color theme, sound, and fullscreen
- Friends screen with friends list and direct conversation actions
- Friend requests screen with incoming/outgoing pending request management
- Send friend request by user ID for development until user search exists
- Blocked users screen with unblock action
- Conversations list screen
- Direct message thread screen with text send, read marking, refresh, and soft-delete for own messages
- Admin dashboard route at `/admin` with admin/super_admin role visibility
- Admin screens for news, announcements, time controls, tournaments, leaderboard, audit logs, and
  read-only operational lists
- Tournament manager UI for registrations, rounds, manual pairings, automatic pairing generation,
  result submission, and standings

## Auth Flow

The app uses these backend endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Access and refresh tokens are stored through a token storage abstraction. Mobile/desktop builds use
`flutter_secure_storage`. Tests can override storage with in-memory storage.

The refresh flow foundation exists through `AuthRepository.refresh()`. Automatic retry-on-401
interceptor behavior can be added later once the app has more authenticated workflows.

## API Client Behavior

The reusable API client:

- Uses a configurable base URL
- Prefixes API calls with `/api/v1`
- Adds `Authorization: Bearer <access_token>` when a token exists
- Adds `X-Request-ID` to every request
- Parses the backend standard error envelope
- Avoids logging tokens or secrets

Backend errors are parsed from:

```json
{
  "error": {
    "code": "auth.unauthorized",
    "message": "Authentication required",
    "details": {},
    "request_id": "..."
  }
}
```

## Pagination

The Flutter helper supports the backend's current list shape:

```json
{
  "items": [],
  "limit": 20,
  "offset": 0,
  "total": 100
}
```

It also supports the newer documented shape with a nested `pagination` object for future endpoint
standardization.

## Initial Screens

Current screens:

- Splash
- Login
- Register
- Home
- News list
- News detail
- Tournament list
- Tournament detail
- Leaderboard
- Games list
- Game detail and replay board
- PGN import
- Chess clock
- Friends
- Friend requests
- Blocked users
- Conversations
- Conversation detail
- Admin dashboard
- Admin news
- Admin announcements
- Admin time controls
- Admin tournaments
- Admin tournament manager
- Admin leaderboard
- Admin audit logs
- Notifications
- Profile

The home screen consumes:

- `GET /api/v1/home`

Other screen endpoints:

- News: `GET /api/v1/news`
- News detail: `GET /api/v1/news/{slug}`
- Tournaments: `GET /api/v1/tournaments`
- Tournament detail: `GET /api/v1/tournaments/{slug}`
- Tournament register: `POST /api/v1/tournaments/{tournament_id}/register`
- Tournament cancel registration: `DELETE /api/v1/tournaments/{tournament_id}/registration`
- Tournament rounds: `GET /api/v1/tournaments/{slug}/rounds`
- Tournament standings: `GET /api/v1/tournaments/{slug}/standings`
- Leaderboard: `GET /api/v1/leaderboard`
- Seasons: `GET /api/v1/leaderboard/seasons`
- Games: `GET /api/v1/games`
- Game detail: `GET /api/v1/games/{game_id}`
- PGN paste: `POST /api/v1/games/pgn/paste`
- Analysis request: `POST /api/v1/games/{game_id}/analysis`
- Game analysis state: `GET /api/v1/games/{game_id}/analysis`
- Analysis job: `GET /api/v1/analysis/jobs/{job_id}`
- Analysis report: `GET /api/v1/analysis/reports/{report_id}`
- Clock create: `POST /api/v1/clock/sessions`
- Clock events: `GET /api/v1/clock/sessions/{session_id}/events`
- Clock start: `POST /api/v1/clock/sessions/{session_id}/start`
- Clock pause: `POST /api/v1/clock/sessions/{session_id}/pause`
- Clock resume: `POST /api/v1/clock/sessions/{session_id}/resume`
- Clock switch turn: `POST /api/v1/clock/sessions/{session_id}/switch-turn`
- Clock adjust: `POST /api/v1/clock/sessions/{session_id}/adjust`
- Clock flag: `POST /api/v1/clock/sessions/{session_id}/flag`
- Clock complete: `POST /api/v1/clock/sessions/{session_id}/complete`
- Clock reset: `POST /api/v1/clock/sessions/{session_id}/reset`
- Clock cancel: `POST /api/v1/clock/sessions/{session_id}/cancel`
- Friend requests: `GET /api/v1/friends/requests`
- Send friend request: `POST /api/v1/friends/requests`
- Accept friend request: `POST /api/v1/friends/requests/{request_id}/accept`
- Reject friend request: `POST /api/v1/friends/requests/{request_id}/reject`
- Cancel friend request: `POST /api/v1/friends/requests/{request_id}/cancel`
- Friends: `GET /api/v1/friends`
- Remove friend: `DELETE /api/v1/friends/{user_id}`
- Blocks: `GET /api/v1/blocks`
- Block user: `POST /api/v1/blocks`
- Unblock user: `DELETE /api/v1/blocks/{blocked_id}`
- Conversations: `GET /api/v1/conversations`
- Direct conversation: `POST /api/v1/conversations/direct`
- Conversation detail: `GET /api/v1/conversations/{conversation_id}`
- Conversation messages: `GET /api/v1/conversations/{conversation_id}/messages`
- Send message: `POST /api/v1/conversations/{conversation_id}/messages`
- Mark conversation read: `POST /api/v1/conversations/{conversation_id}/read`
- Delete own message: `DELETE /api/v1/messages/{message_id}`
- Admin identity: `GET /api/v1/admin/me`
- Admin news: `GET /api/v1/admin/news`
- Create admin news: `POST /api/v1/admin/news`
- Update admin news: `PATCH /api/v1/admin/news/{article_id}`
- Publish/archive/delete admin news:
  `POST /api/v1/admin/news/{article_id}/publish`,
  `POST /api/v1/admin/news/{article_id}/archive`,
  `DELETE /api/v1/admin/news/{article_id}`
- Admin announcements: `GET /api/v1/admin/announcements`
- Create/update/publish/archive/delete admin announcements under `/api/v1/admin/announcements`
- Admin time controls: `GET/POST/PATCH /api/v1/admin/time-controls`
- Admin tournaments and lifecycle actions under `/api/v1/admin/tournaments`
- Admin tournament registrations:
  `GET /api/v1/admin/tournaments/{tournament_id}/registrations`
  and `PATCH /api/v1/admin/tournament-registrations/{registration_id}`
- Admin rounds, pairings, results, and standings under `/api/v1/admin/rounds`,
  `/api/v1/admin/pairings`, and `/api/v1/admin/tournaments/{tournament_id}/standings`
- Admin automatic pairing generation:
  `POST /api/v1/admin/rounds/{round_id}/pairings/generate`
- Admin leaderboard seasons/recompute: `/api/v1/admin/leaderboard`
- Admin audit logs: `GET /api/v1/admin/audit-logs`
- Admin read-only lists: games, analysis jobs, Chess.com sync jobs, and notifications
- Notifications: `GET /api/v1/notifications`
- Unread count: `GET /api/v1/notifications/unread-count`
- Mark notification read: `POST /api/v1/notifications/{notification_id}/read`
- Mark all notifications read: `POST /api/v1/notifications/read-all`
- Profile: `GET /api/v1/users/me`
- Profile update: `PATCH /api/v1/users/me/profile`

## Realtime / SSE

The backend SSE endpoint is:

```text
GET /api/v1/realtime/stream
```

Phase 15 includes a small `RealtimeService` that exposes the stream URI. Full Flutter SSE
subscription and UI handling are future work. Flutter should treat SSE events as lightweight hints
and refetch full REST state after important events.

## Placeholders

Game library and analysis-board behavior:

- The board is read-only and is rendered from backend FEN data.
- Users can jump to the start, previous move, next move, final move, or a selected SAN move.
- The latest move is highlighted from UCI coordinates when available.
- PGN paste is implemented. File upload remains a future UI extension while backend support already exists.
- Analysis can be requested from a game detail screen.
- Queued/running/failed/completed analysis states are shown, with manual refresh for job status.
- Completed reports show approximate accuracies, classification counts, selected-move evaluation, centipawn loss, best move, and principal variation data.

Chess clock behavior:

- The Flutter client runs the visible countdown locally for responsive tapping.
- The backend is called only for meaningful events: create, start, pause, resume, switch turn,
  adjust time, flag, complete, reset, and cancel.
- Switch-turn applies increment on the client before sending the snapshot to the backend.
- Event history reads backend `clock_events` snapshots and is newest-first in the UI.
- The current UI focuses on casual clock sessions. Official tournament/pairing clock workflows are
  backend-supported but not yet exposed as a dedicated Flutter flow.
- Sound and fullscreen controls are UI placeholders; no audio/vibration/fullscreen implementation is
  active yet.

Friends and direct chat behavior:

- Friends is exposed as a secondary app-bar action, not a bottom navigation tab, to keep mobile
  navigation readable.
- Friend requests can be sent by receiver user ID. Proper user search/discovery is a future backend
  and UI improvement.
- Incoming requests can be accepted or rejected.
- Outgoing pending requests can be cancelled.
- Friends can be removed, blocked, or opened as direct conversations.
- Blocking and unblocking use the existing backend safety rules.
- Conversations list shows direct conversations and last-message summaries.
- Conversation detail supports text messages only.
- Message send validates non-empty text in the UI before calling the backend.
- The thread marks the conversation as read on open and after send as a best-effort call.
- Users can soft-delete their own messages; deleted messages render as a sanitized deleted state.
- SSE refetch integration is not wired in Phase 19; REST refresh remains authoritative.

Admin dashboard behavior:

- Admin entry is shown only when the authenticated `CurrentUser.roles` contains `admin` or
  `super_admin`.
- Admin routes still call `GET /api/v1/admin/me` so the backend remains the authority.
- Non-admin users who navigate manually to `/admin` see a forbidden state.
- The admin dashboard uses a sidebar on wide layouts and a section picker on compact layouts.
- Content management supports create/edit/publish/archive/delete for news and announcements.
- Tournament management supports create/edit/lifecycle actions, registration status updates, round
  creation/status actions, manual pairing creation, automatic Swiss or round-robin generation,
  result submission, and standings viewing.
- Generated pairings remain regular pairings that admins can manually review and edit before
  results are submitted.
- Player and user selection uses ID inputs where the backend does not yet expose search/picker
  endpoints.
- Operational admin lists for games, analysis jobs, Chess.com sync jobs, and notifications are
  read-only.

Still placeholder or future UI work:

- PGN file upload UI
- Chess.com import UI
- Official tournament clock setup flow
- User search/discovery for friend requests
- Group chat UI
- Tournament chat UI
- Media messages
- SSE event consumption
- Rich markdown editor for admin news
- User search/player picker for admin forms
- Drag/drop pairing tools
- FIDE-certified pairing and advanced color-history optimization
- Draggable board input
- Engine arrows
- Evaluation graph
- Sound/vibration cues for chess clock
- Offline clock mode

## Recommended Next Flutter Phase

Recommended next UI phase:

- Add Chess.com import UI, PGN file upload UI, admin UI polish, or SSE-driven social refresh after
  Ibrahim chooses the next product slice.
- Add PGN file upload, engine arrows, and an evaluation graph as later game-review refinements.
