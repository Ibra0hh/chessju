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

Checks:

```powershell
flutter analyze
flutter test
flutter build web
```

See `../../docs/FLUTTER_APP.md` for the current app structure and integration notes.
