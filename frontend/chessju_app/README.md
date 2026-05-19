# ChessJU Flutter App

Flutter client foundation for ChessJU.

Run locally against the backend on `http://localhost:8001`:

```powershell
flutter pub get
flutter run -d chrome --dart-define=CHESSJU_API_BASE_URL=http://localhost:8001
```

Android emulator uses the host alias:

```powershell
flutter run -d emulator --dart-define=CHESSJU_API_BASE_URL=http://10.0.2.2:8001
```

iOS simulator on macOS can use `http://localhost:8001`. The iOS project files are included, but
iOS build, signing, TestFlight, and App Store release require macOS with Xcode and are not run from
Windows.

Checks:

```powershell
flutter analyze
flutter test
flutter build web
```

See `../../docs/FLUTTER_APP.md` for the current app structure and integration notes.

Current vertical slice:

- Auth splash/login/register/logout
- Home, news list/detail, tournaments list/detail, leaderboard, games list, notifications, profile
- Tournament registration/cancellation
- Notification read/read-all
- Profile edit for full name, University ID, and Chess.com username
- Game library filtering by source
- Game detail with read-only FEN board replay
- PGN paste import
- Stockfish analysis request/status/report display
- Chess clock screen with casual setup, local countdown, backend event snapshots, and event history
- Friends screen, friend requests, block management, conversations, and direct text messages
- Admin dashboard foundation with content management, tournament manager, leaderboard recompute,
  audit logs, and read-only operational lists
- Admin tournament manager automatic Swiss/Round Robin pairing generation for selected rounds

Current game-review limitations:

- PGN file upload UI is not implemented yet, though the backend endpoint exists.
- The board is replay-only; there is no draggable move input.
- Engine arrows and evaluation graph are not implemented yet.

Current clock limitations:

- The Flutter flow creates casual clock sessions only.
- Official tournament/pairing clock backend support is not exposed as a dedicated Flutter workflow yet.
- Sound and fullscreen controls are placeholders.
- There is no offline mode or clock drift reconciliation UI.

Current social/chat limitations:

- Friend requests use a receiver user ID field because user search/discovery is not implemented yet.
- Direct chat is text-only.
- Group chat, tournament chat, media messages, and push notifications are not implemented.
- SSE-driven chat refresh is not wired yet; screens use REST refreshes as the source of truth.

Current admin limitations:

- Admin user and player selection uses raw IDs until search/picker endpoints exist.
- News editing uses a plain text markdown field, not a rich editor.
- Generated pairings can be reviewed and edited manually; there is no drag/drop pairing board or
  FIDE-certified pairing engine.
- Operational games, analysis, Chess.com sync, and notifications admin panels are read-only.
- iOS builds are not run from Windows.
