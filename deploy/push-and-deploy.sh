#!/usr/bin/env bash
# 수동 폴백(정식 경로는 CI .github/workflows/deploy.yml). 개발 PC에서 실행:
# 이미지 빌드·푸시(프론트 포함, 컨텍스트 레포 루트) → env·compose·스크립트 서버 전송 → 서버 배포 스크립트 원격 실행
# 사용: IMAGE=ghcr.io/<owner>/kbap-pm-agent REMOTE_DIR=<서버 디렉토리> ./deploy/push-and-deploy.sh <ssh-host>
# 운영 env는 레포 루트 .env.prod (gitignore 대상). 사전 docker login ghcr.io 필요
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -lt 1 ]; then
  echo "사용: IMAGE=ghcr.io/<owner>/kbap-pm-agent REMOTE_DIR=<서버 디렉토리> $0 <ssh-host>" >&2
  exit 1
fi
HOST=$1
: "${IMAGE:?IMAGE 필요 (예: ghcr.io/<owner>/kbap-pm-agent)}"
: "${REMOTE_DIR:?REMOTE_DIR 필요 (서버의 배포 파일 디렉토리)}"
TAG="$(git rev-parse --short HEAD)"

[ -f .env.prod ] || { echo ".env.prod 없음 (cp deploy/kbap-pm-agent.env.example .env.prod 후 값 입력)"; exit 1; }

echo "[1/3] 이미지 빌드·푸시 (amd64+arm64): 태그 $TAG"
docker buildx build --platform linux/amd64,linux/arm64 -f backend/Dockerfile -t "$IMAGE:latest" -t "$IMAGE:$TAG" --push .

echo "[2/3] 서버로 파일 전송"
scp -q .env.prod                                "$HOST:$REMOTE_DIR/kbap-pm-agent.env"
scp -q deploy/docker-compose.kbap-pm-agent.yml  "$HOST:$REMOTE_DIR/"
scp -q deploy/deploy.kbap-pm-agent.sh           "$HOST:$REMOTE_DIR/"
ssh "$HOST" "chmod 600 $REMOTE_DIR/kbap-pm-agent.env && chmod +x $REMOTE_DIR/deploy.kbap-pm-agent.sh"

echo "[3/3] 서버 배포 스크립트 실행"
ssh "$HOST" "COMPOSE_FILE=$REMOTE_DIR/docker-compose.kbap-pm-agent.yml ENV_FILE=$REMOTE_DIR/kbap-pm-agent.env \
  IMAGE=$IMAGE IMAGE_TAG=$TAG $REMOTE_DIR/deploy.kbap-pm-agent.sh"
echo "배포된 태그: $TAG"
