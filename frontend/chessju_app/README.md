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

Current game-review limitations:

- PGN file upload UI is not implemented yet, though the backend endpoint exists.
- The board is replay-only; there is no draggable move input.
- Engine arrows and evaluation graph are not implemented yet.
