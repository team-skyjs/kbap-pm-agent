#!/usr/bin/env bash
# 서버에서 실행: pull → up → 백엔드·웹·nginx 경유 API 헬스 확인
# CI(self-hosted 러너)가 COMPOSE_FILE·ENV_FILE·IMAGE·IMAGE_WEB·IMAGE_TAG를 넘김. 수동 실행도 같은 변수 필수
set -euo pipefail

: "${COMPOSE_FILE:?COMPOSE_FILE 필요 (deploy/docker-compose.kbap-pm-agent.yml 경로)}"
: "${ENV_FILE:?ENV_FILE 필요 (운영 env 파일 경로)}"
: "${IMAGE:?IMAGE 필요}"
: "${IMAGE_WEB:?IMAGE_WEB 필요}"
export ENV_FILE IMAGE IMAGE_WEB
export IMAGE_TAG="${IMAGE_TAG:-latest}"
NAME="kbap-pm-agent"

echo "==============================="
echo "$NAME 배포 시작: $(date)  태그 $IMAGE_TAG"
echo "==============================="

[ -f "$ENV_FILE" ] || { echo "ENV_FILE 없음. deploy/kbap-pm-agent.env.example 참고"; exit 1; }

echo "[1/4] 이미지 pull"
docker compose -f "$COMPOSE_FILE" pull

echo "[2/4] 컨테이너 기동"
docker compose -f "$COMPOSE_FILE" up -d

# 20회(약 1분) 안에 조건을 만족하는 응답이 오면 통과
wait_for() {  # 이름 URL 검사식(grep -q 패턴) [curl 옵션]
  local name=$1 url=$2 pattern=$3; shift 3
  for i in $(seq 1 20); do
    if body=$(curl -fs "$@" "$url") && grep -q "$pattern" <<<"$body"; then
      echo "$name OK (${i}회차)"; return 0
    fi
    sleep 3
  done
  echo "$name 실패. 로그:"; docker logs --tail 30 "$NAME"; docker logs --tail 30 "$NAME-web"; exit 1
}

echo "[3/4] 헬스체크"
wait_for "백엔드 /api/health" http://127.0.0.1:8001/api/health '"db":"ok"'
wait_for "웹 / (HTML)" http://127.0.0.1:8002/ '<html'
wait_for "웹 경유 /api/health (nginx 프록시)" http://127.0.0.1:8002/api/health '"db":"ok"'

echo "[4/4] 컨테이너 상태"
docker ps | grep "$NAME" || true
docker image prune -f >/dev/null   # 이전 레이어 정리

echo "$NAME 배포 완료: $(date)"
