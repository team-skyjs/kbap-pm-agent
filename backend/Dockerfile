FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY schema.sql ./
COPY app ./app
COPY checks ./checks
EXPOSE 8000
# ponytail: 단일 워커. SSE 실행 상태·OAuth 대기·요약 백그라운드 스레드가 프로세스 메모리에 있음. 사용자 2명이라 충분, 늘면 상태를 DB/큐로
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
