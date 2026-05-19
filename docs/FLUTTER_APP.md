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

Implemented in Phases 15-16:

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

Still placeholder or future UI work:

- Game detail UI
- PGN paste/upload UI
- Analysis report UI
- Chess.com import UI
- Chess clock UI
- Friends/direct chat UI
- SSE event consumption
- Admin dashboard UI

## Recommended Next Flutter Phase

Recommended next UI phase:

- Build the game detail and analysis-board UI using `games`, `game_moves`, and analysis report data.
- Add PGN paste/upload forms once the game detail screen exists.
- Add clock and chat UI after the core chess game review surface is usable.
