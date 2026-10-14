"""메시지 SSE 검사: fake 실행 SSE 순서, final이 Message 모델 통과, GET 상세와 동일, 실행 중 409, 스트림 전 에러, 끊김 마감."""
import json
import os
import time

from common import client, ok

from app import db
from app.conversations import fail_stale_runs
from app.schemas import Message, ToolCall


def events(resp) -> list[tuple[str, dict]]:
    out, ev = [], None
    for line in resp.iter_lines():
        if line.startswith("event: "):
            ev = line[7:]
        elif line.startswith("data: "):
            out.append((ev, json.loads(line[6:])))
    return out


c = client()
cid = c.post("/api/conversations", json={}).json()["id"]
q = "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘"
with c.stream("POST", f"/api/conversations/{cid}/messages", json={"content": q}) as r:
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream"), r.status_code
    assert r.headers["cache-control"] == "no-cache" and r.headers["x-accel-buffering"] == "no"
    evs = events(r)

names = [e for e, _ in evs]
assert names == ["message_created", "tool_call", "tool_result", "tool_call", "tool_result", "final"], names
mc = evs[0][1]
assert set(mc) == {"userMessage", "assistantMessageId"}
um = Message.model_validate(mc["userMessage"])
assert um.role == "user" and um.status == "completed" and um.content == q and um.usage is None
for (e, d), (e2, d2) in [(evs[1], evs[2]), (evs[3], evs[4])]:
    t1, t2 = ToolCall.model_validate(d), ToolCall.model_validate(d2)
    assert t1.id == t2.id and t1.status == "running" and t1.result_summary is None and t1.duration_ms is None
    assert t2.status == "succeeded" and t2.result_summary and t2.duration_ms is not None
assert [evs[1][1]["source"], evs[3][1]["source"]] == ["taxonomy", "code"]
ok("이벤트 순서 message_created → 도구 2쌍 → final, ToolCall 모델 통과")

final = evs[-1][1]
m = Message.model_validate(final)
assert m.model_dump(by_alias=True) == final
assert list(final["proposals"][1]["evidence"][1]) == ["kind", "summary", "file", "function", "line", "snippet"]
assert m.id == mc["assistantMessageId"] and m.status == "completed" and m.error_code is None
assert [p.type for p in m.proposals] == ["improvement", "funnel_design"] and [p.seq for p in m.proposals] == [1, 2]
assert all(p.decision.status == "pending" for p in m.proposals)
assert m.usage is not None and m.usage.cost_usd == 0
assert [t.seq for t in m.tool_calls] == [1, 2]
ok("final = Message, 제안 2개(improvement, funnel_design), usage.costUsd 0")

d = c.get(f"/api/conversations/{cid}").json()
assert d["title"] == q[:40]
assert d["messages"][0] == mc["userMessage"] and d["messages"][1] == final, (d["messages"][1], final)
ok("GET 상세 = message_created.userMessage + final, 제목 앞 40자")

# 실행 중 재전송 → 409 (running 메시지를 직접 넣어 재현)
rid = db.x("INSERT INTO messages (conversation_id, role, status, content) VALUES (%s,'assistant','running','')", (cid,))
r = c.post(f"/api/conversations/{cid}/messages", json={"content": "또"})
assert r.status_code == 409 and r.json()["error"]["code"] == "RUN_IN_PROGRESS", r.text
rm = next(x for x in c.get(f"/api/conversations/{cid}").json()["messages"] if x["id"] == rid)
assert rm["status"] == "running" and rm["content"] == "" and rm["proposals"] == [] and rm["usage"] is None
fail_stale_runs()
rm = next(x for x in c.get(f"/api/conversations/{cid}").json()["messages"] if x["id"] == rid)
assert rm["status"] == "failed" and rm["errorCode"] == "INTERNAL_ERROR"
ok("running 중 409 RUN_IN_PROGRESS, running 메시지 필드 규칙, 기동 시 고아 실행 failed 마감")

for bad in [{"content": ""}, {"content": "x" * 4001}, {}]:
    r = c.post(f"/api/conversations/{cid}/messages", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", r.text
r = c.post("/api/conversations/999999/messages", json={"content": "x"})
assert r.status_code == 404 and r.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"
ok("스트림 전 JSON 에러: 400, 404")

# ping: 대기 중 주석 줄 (간격을 줄여 확인)
import app.conversations as conv_mod  # noqa: E402

conv_mod.PING_SECONDS, os.environ["FAKE_DELAY_SECONDS"] = 0.2, "0.5"
cid3 = c.post("/api/conversations", json={}).json()["id"]
with c.stream("POST", f"/api/conversations/{cid3}/messages", json={"content": "ping 시험"}) as r:
    raw = list(r.iter_lines())
conv_mod.PING_SECONDS, os.environ["FAKE_DELAY_SECONDS"] = 15, "0"
assert ": ping" in raw and raw[-2].startswith("data: ") and raw[-3] == "event: final", raw[-4:]
ok("대기 중 : ping 주석, 마지막 이벤트 final")

# 끊김: TestClient는 연결 끊김을 앱에 전달하지 않아 실제 uvicorn으로 첫 이벤트만 읽고 닫기
import threading  # noqa: E402

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from app.main import app  # noqa: E402

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning", lifespan="off"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.05)
os.environ["FAKE_DELAY_SECONDS"] = "0.5"
cid2 = c.post("/api/conversations", json={}).json()["id"]
with httpx.stream("POST", f"http://127.0.0.1:8765/api/conversations/{cid2}/messages", json={"content": "끊김 시험"}) as r:
    first = next(r.iter_lines())
    assert first == "event: message_created", first
for _ in range(50):
    a = c.get(f"/api/conversations/{cid2}").json()["messages"][1]
    if a["status"] != "running":
        break
    time.sleep(0.1)
os.environ["FAKE_DELAY_SECONDS"] = "0"
assert a["status"] == "failed" and a["errorCode"] == "INTERNAL_ERROR", a
ok("클라이언트 끊김 → failed / INTERNAL_ERROR")
server.should_exit = True
print("check_b3 OK")
