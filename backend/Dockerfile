# 빌드 컨텍스트는 레포 루트: docker build -f backend/Dockerfile .
# 1단계: 프론트 빌드(정적 파일). 같은 출처라 API 주소 빌드 인자 없음
FROM node:22-alpine AS web
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend .
# 빌드 산출물 검사(자산 경로, 절대 API 주소 없음)를 이미지 빌드 단계에서 함께 실행
RUN npm run build && npm run check -- f6

# 2단계: 백엔드가 API와 정적 파일을 함께 서빙(컨테이너 하나)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY backend/schema.sql ./
COPY backend/app ./app
COPY backend/checks ./checks
COPY --from=web /app/dist ./static
EXPOSE 8000
# ponytail: 단일 워커. SSE 실행 상태·OAuth 대기·요약 백그라운드 스레드가 프로세스 메모리에 있음. 사용자 2명이라 충분, 늘면 상태를 DB/큐로
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
