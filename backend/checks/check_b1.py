"""뼈대 검사: health, 404 공통 에러, CORS preflight, ACCESS_TOKEN(인증이 라우팅보다 먼저)"""
import os

from common import client, ok

c = client()

r = c.get("/api/health")
assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok", "version": "0.1.0"}, r.text
ok("health ok")

r = c.get("/api/nope")
assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND", r.text
assert set(r.json()["error"]) == {"code", "message"}
ok("404 NOT_FOUND 공통 형식")

r = c.options("/api/conversations", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                              "Access-Control-Request-Headers": "authorization,content-type"})
assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173", r.headers
assert "authorization" in r.headers["access-control-allow-headers"].lower()
ok("CORS preflight")

os.environ["ACCESS_TOKEN"] = "s3cret"
try:
    assert c.get("/api/health").status_code == 200
    r = c.get("/api/nope")
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED", r.text
    assert r.headers.get("access-control-allow-origin") is None  # Origin 없는 요청
    r = c.get("/api/nope", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 404, r.text
    r = c.get("/api/integrations/amplitude/callback")
    assert r.status_code != 401
    assert c.get("/index.html").status_code != 401  # 화면 파일은 토큰 검사 대상 아님(브라우저가 토큰을 못 붙임)
    r = c.options("/api/conversations", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.status_code == 200
    ok("ACCESS_TOKEN 설정: health 200, /api/nope 401, 토큰 있으면 404, 화면 경로는 토큰 검사 제외, preflight 통과")
finally:
    os.environ["ACCESS_TOKEN"] = ""
assert c.get("/api/nope").status_code == 404
ok("ACCESS_TOKEN 미설정: /api/nope 404")
print("check_b1 OK")
