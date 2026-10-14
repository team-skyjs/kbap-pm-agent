"""운영 검사: Cloudflare Access 서비스 토큰으로 바깥 경로(Access → 터널 → 컨테이너) 전체 확인.
- 토큰 있음: / 가 HTML, /api/health 가 계약 JSON, SSE 100초 이상 유지(서버가 AGENT_MODE=fake, FAKE_DELAY_SECONDS=21 이상일 때만)
- 토큰 없음: API 호출이 백엔드에 닿지 않음(계약 JSON이 아님), X-Requested-With면 401
- 다른 출처 preflight 불허
실행: PUBLIC_BASE_URL=https://<운영 호스트명> CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... uv run python checks/check_b8.py
호스트명은 출력하지 않음(CI 로그에 Variables가 마스킹되지 않아서)."""
import os
import sys
import time

import httpx

base = os.environ["PUBLIC_BASE_URL"].rstrip("/")
token = {"CF-Access-Client-Id": os.environ["CF_ACCESS_CLIENT_ID"],
         "CF-Access-Client-Secret": os.environ["CF_ACCESS_CLIENT_SECRET"]}
app_auth = {"Authorization": f"Bearer {os.environ['ACCESS_TOKEN']}"} if os.environ.get("ACCESS_TOKEN") else {}
fails = 0


def report(ok: bool, name: str, detail: str = "", warn: bool = False) -> None:
    global fails
    tag = "PASS" if ok else ("WARN" if warn else "FAIL")
    fails += not ok and not warn
    print(f"{tag} {name}" + (f" ({detail})" if detail and not ok else ""))


def shape(r: httpx.Response) -> str:
    """호스트·헤더 값 없이 응답 모양만: 상태 코드와 content-type."""
    return f"{r.status_code} {r.headers.get('content-type', '-').split(';')[0]}"


def backend_json(r: httpx.Response) -> bool:
    """백엔드가 만든 응답인지: 계약 JSON(health·목록·에러 형식)."""
    if not r.headers.get("content-type", "").startswith("application/json"):
        return False
    try:
        body = r.json()
    except ValueError:
        return False
    return isinstance(body, dict) and bool({"status", "items", "error", "id"} & set(body))


def get(path: str, headers: dict, **kw) -> httpx.Response:
    return httpx.get(f"{base}{path}", headers=headers, timeout=15, follow_redirects=False, **kw)


def guarded(name: str, fn) -> None:
    """네트워크 오류도 FAIL 한 줄로(트레이스백에 호스트가 찍히지 않게)."""
    try:
        fn()
    except httpx.HTTPError as e:
        report(False, name, f"요청 실패 {type(e).__name__}")


# --- 토큰 있음: 같은 출처 화면과 API
def page():
    r = get("/", token)
    report(r.status_code == 200 and r.headers.get("content-type", "").startswith("text/html"), "토큰: / 가 200 HTML", shape(r))


def health():
    r = get("/api/health", token)
    ok = r.status_code == 200 and backend_json(r) and r.json() == {"status": "ok", "db": "ok", "version": "0.1.0"}
    report(ok, "토큰: /api/health 계약 JSON", shape(r))


guarded("토큰: / 가 200 HTML", page)
guarded("토큰: /api/health 계약 JSON", health)

# --- 토큰 없음: Access에서 멈춰 백엔드 응답이 아니어야 함
# 메시지 전송은 없는 대화 0번으로: 게이트가 뚫려도 404로 끝나 에이전트 실행(LLM 비용)이 생기지 않음
for name, req in [("GET /api/health", lambda h: get("/api/health", h)),
                  ("GET /api/conversations", lambda h: get("/api/conversations", h)),
                  ("POST 메시지 전송", lambda h: httpx.post(f"{base}/api/conversations/0/messages", json={"content": "x"},
                                                         headers=h, timeout=15, follow_redirects=False))]:
    try:
        r = req({})
        report(not backend_json(r), f"토큰 없음: {name} 이 백엔드에 닿지 않음", shape(r))
    except httpx.HTTPError as e:
        report(False, f"토큰 없음: {name} 이 백엔드에 닿지 않음", f"요청 실패 {type(e).__name__}")
def xrw():
    r = get("/api/health", {"X-Requested-With": "XMLHttpRequest"})
    # 401은 Cloudflare 문서상 동작이라 가정. 아니어도 프론트는 302·HTML로 판정하므로 경고만
    report(r.status_code == 401 and not backend_json(r), "토큰 없음 + X-Requested-With: 401", shape(r), warn=True)


guarded("토큰 없음 + X-Requested-With: 401", xrw)

# --- 다른 출처 preflight: 같은 출처라 어떤 출처도 허용하지 않아야 함
def preflight():
    r = httpx.options(f"{base}/api/conversations", timeout=15, follow_redirects=False,
                      headers={**token, "Origin": "https://evil.example.com", "Access-Control-Request-Method": "POST",
                               "Access-Control-Request-Headers": "content-type"})
    report("access-control-allow-origin" not in r.headers, "다른 출처 preflight 불허", shape(r))


guarded("다른 출처 preflight 불허", preflight)

# --- SSE 장시간: 터널·Access가 스트림을 끊지 않는지(fake 지연 실행일 때만)
# 설정 조회는 필수 단언: 401 등 계약 JSON 에러가 와도 SKIP으로 새지 않게 상태 200과 설정 모양을 먼저 확인
mode = None
try:
    s = get("/api/settings", {**token, **app_auth})
    body = s.json() if s.headers.get("content-type", "").startswith("application/json") else {}
    ok = s.status_code == 200 and isinstance(body, dict) and {"agentMode", "budget", "models"} <= set(body)
    report(ok, "토큰: /api/settings 200 설정 객체", shape(s))
    mode = body.get("agentMode") if ok else None
except (httpx.HTTPError, ValueError) as e:
    report(False, "토큰: /api/settings 200 설정 객체", f"요청 실패 {type(e).__name__}")
if mode != "fake":
    print("SKIP SSE 100초 검사: 서버가 fake 모드가 아님(FAKE_DELAY_SECONDS=21로 잠시 띄워 확인)")
else:
    h = {**token, **app_auth}
    cid = httpx.post(f"{base}/api/conversations", json={}, headers=h, timeout=15).json()["id"]
    t0, names, pings = time.monotonic(), [], 0
    try:
        with httpx.stream("POST", f"{base}/api/conversations/{cid}/messages", json={"content": "SSE 장시간 시험"},
                          headers=h, timeout=httpx.Timeout(15, read=60)) as r:
            for line in r.iter_lines():
                if line.startswith("event: "):
                    names.append(line[7:])
                pings += line == ": ping"
    except httpx.HTTPError as e:
        names.append(f"끊김 {type(e).__name__}")
    took = time.monotonic() - t0
    report(bool(names) and names[-1] == "final" and took >= 100, f"SSE {took:.0f}초 유지, ping {pings}회, 마지막 final",
           f"마지막 {names[-1] if names else '없음'}")

print("check_b8 OK" if fails == 0 else f"check_b8 FAIL ({fails})")
sys.exit(1 if fails else 0)
