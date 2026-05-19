# ChessJU Setup

The preferred local environment is Docker Desktop with WSL2 on Windows.

Prerequisites:

- WSL2 installed and enabled
- Docker Desktop installed
- Docker Desktop configured to use the WSL2 backend
- `docker compose` available from the terminal

Copy environment settings:

```powershell
Copy-Item .env.example .env
```

Local storage:

- `CHESSJU_LOCAL_STORAGE_ROOT` controls where uploaded files are stored.
- Docker development uses `/data/storage`, backed by the `chessju_storage` volume.
- Do not commit local uploaded files or `.env`.

Stockfish analysis:

- `CHESSJU_STOCKFISH_PATH` points to the Stockfish binary.
- Docker worker development uses `/usr/games/stockfish`.
- Analysis jobs are queued through Valkey/RQ and processed by the worker service.
- Do not run Stockfish directly inside API request handlers.

Start local services:

```powershell
docker compose -f infra/docker-compose.dev.yml up --build
```

Phase 1 endpoint checks:

```powershell
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8001/version
Invoke-RestMethod http://localhost:8001/health/db
```

Run backend tests:

```powershell
cd backend
python -m pytest
```
