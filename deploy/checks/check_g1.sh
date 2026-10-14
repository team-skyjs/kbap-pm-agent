#!/usr/bin/env bash
# 검사: 백엔드 정적 서빙 같은 출처 동작 (정적 HTML, /api 헬스, SSE 첫 진행 5초 이내와 final 종료)
# 실행: docker compose up -d --build && deploy/checks/check_g1.sh   (기본 BASE=http://localhost:8000, 백엔드 fake 모드)
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
fail() { echo "FAIL: $*" >&2; exit 1; }

got=$(curl -s -o /dev/null -w '%{http_code} %{content_type}' "$BASE/" || true)
[[ $got == "200 text/html"* ]] || fail "GET / → $got"

health=$(curl -s "$BASE/api/health")
python3 -c 'import json,sys; assert json.loads(sys.argv[1]) == {"status":"ok","db":"ok","version":"0.1.0"}' "$health" \
  || fail "GET /api/health → $health"

conv=$(curl -s -X POST -H 'Content-Type: application/json' -d '{}' "$BASE/api/conversations")
id=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$conv") || fail "POST /api/conversations → $conv"

# 줄 도착 시각을 재야 해서 curl -N 출력을 파이썬이 줄 단위로 읽음
curl -sN -X POST -H 'Content-Type: application/json' \
  -d '{"content":"스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘"}' \
  "$BASE/api/conversations/$id/messages" | python3 -c '
import sys, time
t0 = time.monotonic(); first = None; events = []
for line in sys.stdin:
    if line.startswith("event: "):
        ev = line[7:].strip(); events.append(ev)
        if ev == "tool_call" and first is None: first = time.monotonic() - t0
assert first is not None, f"tool_call 없음: {events}"
assert first <= 5, f"첫 tool_call {first:.2f}s > 5s"
assert events and events[-1] == "final", f"마지막 이벤트가 final 아님: {events}"
print(f"SSE ok: 첫 tool_call {first:.2f}s, 이벤트 {len(events)}개")
' || fail "SSE via $BASE"

echo "check_g1 OK ($BASE)"
