import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "CHESSJU_DATABASE_URL",
    "postgresql+psycopg://chessju:chessju_dev_password@localhost:5432/chessju",
)
os.environ.setdefault("CHESSJU_JWT_SECRET_KEY", "test-secret-key-change-me-32-plus")
os.environ.setdefault(
    "CHESSJU_LOCAL_STORAGE_ROOT",
    str(Path(tempfile.gettempdir()) / "chessju-test-storage"),
)
