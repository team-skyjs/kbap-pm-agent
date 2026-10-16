"""내보내기 기록 검사: 201 응답 키가 계약 예시와 같고 행 1개 생성, 형식 밖 400, 없는 대화 404, 형식별 건수 SQL.
실행: docker compose exec backend uv run python checks/check_b11.py"""
import re

from common import client, db, ok

c = client()
cid = c.post("/api/conversations", json={"title": "내보내기"}).json()["id"]

r = c.post(f"/api/conversations/{cid}/exports", json={"format": "markdown"})
assert r.status_code == 201, r.text
body = r.json()
assert list(body) == ["exportId", "conversationId", "format", "createdAt"], body
assert body["conversationId"] == cid and body["format"] == "markdown" and isinstance(body["exportId"], int), body
assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", body["createdAt"]), body
assert db.one("SELECT COUNT(*) n FROM conversation_exports")["n"] == 1
ok("201 계약 키 + 행 1개")

for bad in [{"format": "docx"}, {}, {"format": "pdf", "extra": 1}]:
    r = c.post(f"/api/conversations/{cid}/exports", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", (bad, r.text)
ok("형식 밖 400 VALIDATION_ERROR")

r = c.post("/api/conversations/999999/exports", json={"format": "pdf"})
assert r.status_code == 404 and r.json()["error"]["code"] == "CONVERSATION_NOT_FOUND", r.text
ok("없는 대화 404")

for f in ["pdf", "markdown"]:
    assert c.post(f"/api/conversations/{cid}/exports", json={"format": f}).status_code == 201
counts = {r["format"]: r["n"] for r in db.q("SELECT format, COUNT(*) AS n FROM conversation_exports GROUP BY format")}
assert counts == {"pdf": 1, "markdown": 2}, counts
ok("형식별 건수 pdf 1, markdown 2")

db.x("DELETE FROM conversations WHERE id = %s", (cid,))
assert db.one("SELECT COUNT(*) n FROM conversation_exports")["n"] == 0
ok("대화 삭제 시 기록 함께 삭제")
