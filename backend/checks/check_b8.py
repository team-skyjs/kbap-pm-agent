"""B8 검사 (운영): PUBLIC_BASE_URL의 health 200, GitHub Pages 출처 preflight, SSE가 100초 이상 끊기지 않음.
SSE 장시간 검사는 서버가 AGENT_MODE=fake, FAKE_DELAY_SECONDS=21 이상일 때만 돈다(이벤트 사이 지연 → 약 105초).
실행: PUBLIC_BASE_URL=https://... [ACCESS_TOKEN=...] uv run python checks/check_b8.py"""
import os
import re
import subprocess
import time

import httpx

base = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
auth = {"Authorization": f"Bearer {os.environ['ACCESS_TOKEN']}"} if os.environ.get("ACCESS_TOKEN") else {}


def expected_origin() -> tuple[str, str]:
    """Pages 출처의 단일 기준은 git remote 소유자다(ADR-18). 서버 CORS_ORIGINS를 기대값으로 쓰지 않는다(동어반복)."""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True,
                             cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    except OSError:  # 컨테이너엔 git 저장소가 없을 수 있다
        url = ""
    m = re.search(r"github\.com[:/]([^/]+)/", url)  # https://github.com/owner/repo(.git), git@github.com:owner/repo.git
    if m:
        return f"https://{m.group(1).lower()}.github.io", "git remote"
    # ponytail: 레포 밖 실행 시 수동 값. 기대 출처를 사람이 넣으므로 틀린 값이 통과할 수 있다. 레포 안에서 실행할 것
    assert os.environ.get("EXPECTED_ORIGIN"), "git remote가 없다. EXPECTED_ORIGIN=https://<owner>.github.io 를 지정"
    return os.environ["EXPECTED_ORIGIN"].rstrip("/"), "EXPECTED_ORIGIN"


origin, origin_source = expected_origin()

r = httpx.get(f"{base}/api/health", timeout=10)
assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok", "version": "0.1.0"}, r.text
print(f"PASS health {base}")

r = httpx.options(f"{base}/api/conversations", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                       "Access-Control-Request-Headers": "authorization,content-type"})
assert r.status_code == 200 and r.headers.get("access-control-allow-origin") == origin, (r.status_code, r.headers)
print(f"PASS preflight Origin {origin} (기대 출처: {origin_source})")

s = httpx.get(f"{base}/api/settings", headers=auth, timeout=10).json()
if s["agentMode"] != "fake":
    print("SKIP SSE 100초 검사: 서버가 fake 모드가 아니다(FAKE_DELAY_SECONDS=21로 잠시 띄워 확인)")
else:
    cid = httpx.post(f"{base}/api/conversations", json={}, headers=auth).json()["id"]
    t0, names, pings = time.monotonic(), [], 0
    with httpx.stream("POST", f"{base}/api/conversations/{cid}/messages", json={"content": "SSE 장시간 시험"},
                      headers=auth, timeout=httpx.Timeout(10, read=60)) as r:
        for line in r.iter_lines():
            if line.startswith("event: "):
                names.append(line[7:])
            pings += line == ": ping"
    took = time.monotonic() - t0
    assert names[-1] == "final", names
    assert took >= 100, f"{took:.0f}초 — FAKE_DELAY_SECONDS를 21 이상으로"
    print(f"PASS SSE {took:.0f}초 유지, ping {pings}회, 마지막 이벤트 final")
print("check_b8 OK")
