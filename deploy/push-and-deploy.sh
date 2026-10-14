#!/usr/bin/env bash
# 개발 PC 에서 실행: 멀티아키 이미지 빌드·푸시 → env/compose/스크립트 서버 전송 → 서버 배포 스크립트 원격 실행
# 사용: ./deploy/push-and-deploy.sh [ssh-host]   (기본 handev). 운영 env는 레포 루트 .env.prod (gitignore됨)
set -e
cd "$(dirname "$0")/.."

HOST="${1:-handev}"
IMAGE="simhani1/kbap-pm-agent"
TAG="$(git rev-parse --short HEAD)"
REMOTE_DIR="/home/simhani1/files"

[ -f .env.prod ] || { echo ".env.prod 없음 (cp deploy/kbap-pm-agent.env.example .env.prod 후 값 입력)"; exit 1; }

echo "[1/3] 이미지 빌드·푸시 (amd64+arm64): $IMAGE:latest, :$TAG"
docker buildx build --platform linux/amd64,linux/arm64 -t "$IMAGE:latest" -t "$IMAGE:$TAG" --push ./backend

echo "[2/3] 서버로 파일 전송 ($HOST:$REMOTE_DIR)"
scp -q .env.prod                                "$HOST:$REMOTE_DIR/kbap-pm-agent.env"
scp -q deploy/docker-compose.kbap-pm-agent.yml  "$HOST:$REMOTE_DIR/"
scp -q deploy/deploy.kbap-pm-agent.sh           "$HOST:$REMOTE_DIR/"
ssh "$HOST" "chmod 600 $REMOTE_DIR/kbap-pm-agent.env && chmod +x $REMOTE_DIR/deploy.kbap-pm-agent.sh"

echo "[3/3] 서버 배포 스크립트 실행"
ssh "$HOST" "$REMOTE_DIR/deploy.kbap-pm-agent.sh"
echo "배포된 태그: $TAG"
