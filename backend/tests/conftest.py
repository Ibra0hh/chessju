import os

os.environ.setdefault(
    "CHESSJU_DATABASE_URL",
    "postgresql+psycopg://chessju:chessju_dev_password@localhost:5432/chessju",
)
os.environ.setdefault("CHESSJU_JWT_SECRET_KEY", "test-secret-key-change-me-32-plus")
