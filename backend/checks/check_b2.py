"""B2 검사: 계약 예시가 schemas 모델을 통과하고 재직렬화가 원문과 같다. 대화 엔드포인트 shape, PATCH decidedAt 전이."""
import json

from common import client, ok
from examples import CONV_DETAIL, CONV_LIST, CREATED_8, MESSAGE_42, PROPOSAL_15, SETTINGS

from app import db
from app.schemas import ConversationDetail, ConversationSummary, Message, Proposal, Settings

dump = lambda m: m.model_dump(by_alias=True)  # noqa: E731
assert dump(Message.model_validate(MESSAGE_42)) == MESSAGE_42
assert dump(Proposal.model_validate(PROPOSAL_15)) == PROPOSAL_15
assert dump(ConversationDetail.model_validate(CONV_DETAIL)) == CONV_DETAIL
assert [dump(ConversationSummary.model_validate(i)) for i in CONV_LIST["items"]] == CONV_LIST["items"]
assert dump(ConversationSummary.model_validate(CREATED_8)) == CREATED_8
assert dump(Settings.model_validate(SETTINGS)) == SETTINGS
ok("계약 예시 → 모델 → 재직렬화 동일")

c = client()
r = c.post("/api/conversations", json={"title": "장바구니 개선 측정 설계"})
assert r.status_code == 201, r.text
conv = r.json()
assert set(conv) == set(CREATED_8) and conv["title"] == "장바구니 개선 측정 설계" and conv["messageCount"] == 0
ConversationSummary.model_validate(conv)
r = c.post("/api/conversations", json={})
assert r.status_code == 201 and r.json()["title"] is None
assert c.post("/api/conversations").status_code == 201
ok("POST /api/conversations 201, {} / 본문 없음 → title null")

for bad in [{"title": ""}, {"title": "x" * 201}, {"title": 3}]:
    r = c.post("/api/conversations", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", (bad, r.text)
r = c.post("/api/conversations", content="{broken", headers={"content-type": "application/json"})
assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR" and "detail" not in r.json()
ok("잘못된 title·깨진 JSON → 400 VALIDATION_ERROR")

# 시험 메시지·제안을 DB에 직접 넣는다
cid = conv["id"]
mid = db.x("INSERT INTO messages (conversation_id, role, status, content) VALUES (%s,'assistant','completed','본문')", (cid,))
p = PROPOSAL_15
pid = db.x("""INSERT INTO proposals (message_id, conversation_id, seq, type, title, evidence_json, proposal_text, steps_json,
              measurement_json) VALUES (%s,%s,1,%s,%s,%s,%s,%s,%s)""",
           (mid, cid, p["type"], p["title"], json.dumps(p["evidence"]), p["proposal"], json.dumps(p["steps"]),
            json.dumps(p["measurement"])))
db.x("INSERT INTO tool_calls (message_id, seq, source, name, input_json, status, result_summary, duration_ms) VALUES (%s,1,'code','find_event_calls','{\"eventName\":\"a\"}','succeeded','ok',3)", (mid,))

r = c.get(f"/api/conversations/{cid}")
assert r.status_code == 200
d = ConversationDetail.model_validate(r.json())
assert dump(d) == r.json()
m = r.json()["messages"][0]
assert m["usage"] is None and m["toolCalls"][0]["input"] == {"eventName": "a"}
assert m["proposals"][0]["decision"] == {"status": "pending", "note": None, "decidedAt": None}
ok("GET 상세 shape = 모델, decision 기본값")

r = c.get("/api/conversations")
items = r.json()["items"]
mine = next(i for i in items if i["id"] == cid)
assert set(r.json()) == {"items"} and mine["proposalCount"] == 1 and mine["messageCount"] == 1
assert [i["updatedAt"] for i in items] == sorted((i["updatedAt"] for i in items), reverse=True)
ok("GET 목록 items 감싸기, updatedAt 내림차순, 집계")

r = c.patch(f"/api/proposals/{pid}", json={"status": "adopted", "note": "KB-812"})
assert r.status_code == 200, r.text
dec = r.json()["decision"]
assert dec["status"] == "adopted" and dec["note"] == "KB-812" and dec["decidedAt"].endswith("Z")
Proposal.model_validate(r.json())
assert c.get("/api/conversations").json()["items"][0] == {**mine, "adoptedCount": 1, "updatedAt": c.get("/api/conversations").json()["items"][0]["updatedAt"]}  # PATCH가 updated_at 갱신 → 맨 위
r = c.patch(f"/api/proposals/{pid}", json={"status": "on_hold"})
assert r.json()["decision"]["note"] == "KB-812" and r.json()["decision"]["decidedAt"]  # note 생략 → 유지
r = c.patch(f"/api/proposals/{pid}", json={"status": "pending", "note": None})
assert r.json()["decision"] == {"status": "pending", "note": None, "decidedAt": None}, r.json()
ok("PATCH adopted → decidedAt 채움, note 생략 유지, pending+null → 둘 다 null")

for bad in [{"status": "done"}, {}, {"status": "adopted", "note": "x" * 1001}]:
    r = c.patch(f"/api/proposals/{pid}", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", r.text
r = c.patch("/api/proposals/999999", json={"status": "adopted"})
assert r.status_code == 404 and r.json()["error"]["code"] == "PROPOSAL_NOT_FOUND"
r = c.get("/api/conversations/999999")
assert r.status_code == 404 and r.json()["error"] == {"code": "CONVERSATION_NOT_FOUND", "message": "대화 999999을 찾을 수 없습니다."}
ok("잘못된 status 400, 없는 제안·대화 404")
print("check_b2 OK")
