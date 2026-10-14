#!/usr/bin/env bash
# 검사: 배포 구성(두 서비스, 경로·이미지 필수화)과 운영 식별자 미노출
# 실행: 레포 루트에서 deploy/checks/check_g4.sh   (운영 도메인 검사는 PUBLIC_BASE_URL 환경변수가 있을 때만)
set -uo pipefail
cd "$(dirname "$0")/../.."
COMPOSE=deploy/docker-compose.kbap-pm-agent.yml
fails=0
pass() { echo "PASS $*"; }
fail() { echo "FAIL $*"; fails=$((fails + 1)); }
tracked() { git ls-files deploy .github backend frontend | grep -vx "deploy/checks/check_g4.sh"; }   # 검사 패턴을 담은 이 파일 자신은 제외

services=$(IMAGE=x/a IMAGE_WEB=x/b ENV_FILE=/dev/null docker compose -f "$COMPOSE" config --services 2>/dev/null | sort | tr '\n' ' ')
[ "$services" = "kbap-pm-agent kbap-pm-agent-web " ] && pass "compose config: 서비스 kbap-pm-agent·kbap-pm-agent-web" || fail "compose 서비스 = '$services'"

if (unset ENV_FILE; IMAGE=x/a IMAGE_WEB=x/b docker compose -f "$COMPOSE" config >/dev/null 2>&1); then
  fail "ENV_FILE 없이 compose config 성공(필수화 안 됨)"
else
  pass "ENV_FILE 없으면 compose 실패"
fi

# 원격 접속 전에 끝나는지: 가짜 ssh·scp가 불리면 실패로 기록
fake=$(mktemp -d); printf '#!/bin/sh\necho called > "%s/called"\n' "$fake" > "$fake/ssh"; cp "$fake/ssh" "$fake/scp"; chmod +x "$fake/ssh" "$fake/scp"
PATH="$fake:$PATH" deploy/push-and-deploy.sh >/dev/null 2>&1; code=$?
[ "$code" -eq 1 ] && [ ! -e "$fake/called" ] && pass "push-and-deploy.sh 인자 없으면 접속 전 종료 코드 1" || fail "push-and-deploy.sh 인자 없음 → 종료 $code, 원격 호출 $( [ -e "$fake/called" ] && echo 있음 || echo 없음)"
rm -rf "$fake"

alias_lines=$(tracked | grep '\.sh$' | xargs grep -n '\${1:-' 2>/dev/null)
[ -z "$alias_lines" ] && pass "셸 스크립트에 \${1:- 형태 호스트·별칭 기본값 없음" || fail "\${1:- 기본값: $alias_lines"

scan() { tracked | xargs grep -lF -- "$1" 2>/dev/null; }
hits=$(scan "/home/")
[ -z "$hits" ] && pass "서버 사용자 경로(/home/) 없음" || fail "/home/ 포함 파일: $hits"

if [ -n "${PUBLIC_BASE_URL:-}" ]; then
  host=$(python3 -c 'import sys,urllib.parse; print(urllib.parse.urlparse(sys.argv[1]).hostname or "")' "$PUBLIC_BASE_URL")
  hits=$( [ -n "$host" ] && scan "$host" )
  [ -n "$host" ] && [ -z "$hits" ] && pass "운영 도메인 없음(PUBLIC_BASE_URL 호스트 기준, 값은 출력 안 함)" || fail "운영 도메인 포함 파일: ${hits:-호스트 해석 실패}"
else
  echo "SKIP 운영 도메인 검사: PUBLIC_BASE_URL 미설정"
fi

[ "$fails" -eq 0 ] && echo "check_g4 OK" || { echo "check_g4 FAIL ($fails)"; exit 1; }
