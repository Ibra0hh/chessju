FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/backend:/workspace

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/app ./backend/app
COPY worker ./worker

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e "./backend"

CMD ["python", "worker/main.py"]
