#!/usr/bin/env bash
# 서버에서 실행: pull → up → /api/health 확인
# CI(self-hosted 러너)는 COMPOSE_FILE·IMAGE·IMAGE_TAG 를 환경변수로 넘긴다. 수동 실행은 기본값을 쓴다.
set -e

COMPOSE_FILE="${COMPOSE_FILE:-/home/simhani1/files/docker-compose.kbap-pm-agent.yml}"
export ENV_FILE="${ENV_FILE:-/home/simhani1/files/kbap-pm-agent.env}"
export IMAGE="${IMAGE:-ghcr.io/team-skyjs/kbap-pm-agent}"
export IMAGE_TAG="${IMAGE_TAG:-latest}"
NAME="kbap-pm-agent"

echo "==============================="
echo "$NAME 배포 시작: $(date)  이미지 $IMAGE:$IMAGE_TAG"
echo "==============================="

[ -f "$ENV_FILE" ] || { echo "$ENV_FILE 없음. deploy/kbap-pm-agent.env.example 참고해 서버에 만든 뒤 다시 실행"; exit 1; }

echo "[1/4] 이미지 pull"
docker compose -f "$COMPOSE_FILE" pull

echo "[2/4] 컨테이너 기동"
docker compose -f "$COMPOSE_FILE" up -d

echo "[3/4] 헬스체크 (/api/health)"
for i in $(seq 1 20); do
  if body=$(curl -fs http://127.0.0.1:8001/api/health); then
    echo "응답: $body (${i}회차)"
    echo "$body" | grep -q '"db":"ok"' || { echo "DB 연결 실패(degraded). DATABASE_URL 확인"; exit 1; }
    break
  fi
  [ "$i" -eq 20 ] && { echo "20회 안에 응답 없음. 로그:"; docker logs --tail 30 "$NAME"; exit 1; }
  sleep 3
done

echo "[4/4] 컨테이너 상태"
docker ps | grep "$NAME" || true
docker image prune -f >/dev/null   # 이전 레이어 정리

echo "$NAME 배포 완료: $(date)"
