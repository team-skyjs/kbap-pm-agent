"""대화·메시지·제안 라우트."""
import asyncio
import json
import logging
import time

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from app import agent, budget, db
from app.db import iso
from app.errors import ApiError
from pydantic import TypeAdapter

from app.schemas import CreateConversationIn, Evidence, Measurement, PatchProposalIn, SendMessageIn

log = logging.getLogger("app.conversations")
PING_SECONDS = 15
_EVIDENCE = TypeAdapter(list[Evidence])

router = APIRouter(prefix="/api")

SUMMARY_SQL = """SELECT c.id, c.title, c.created_at, c.updated_at,
  (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS mc,
  (SELECT COUNT(*) FROM proposals p WHERE p.conversation_id = c.id) AS pc,
  (SELECT COUNT(*) FROM proposals p WHERE p.conversation_id = c.id AND p.decision_status = 'adopted') AS ac
FROM conversations c"""


def _summary(r: dict) -> dict:
    return {"id": r["id"], "title": r["title"], "createdAt": iso(r["created_at"]), "updatedAt": iso(r["updated_at"]),
            "messageCount": r["mc"], "proposalCount": r["pc"], "adoptedCount": r["ac"]}


def tool_call_dict(r: dict) -> dict:
    return {"id": r["id"], "seq": r["seq"], "source": r["source"], "name": r["name"], "input": json.loads(r["input_json"]),
            "status": r["status"], "resultSummary": r["result_summary"], "durationMs": r["duration_ms"],
            "startedAt": iso(r["started_at"])}


def proposal_dict(r: dict) -> dict:
    return {"id": r["id"], "conversationId": r["conversation_id"], "messageId": r["message_id"], "seq": r["seq"],
            "type": r["type"], "title": r["title"],
            # MySQL JSON 컬럼이 키 순서를 바꿈. 모델을 거쳐 계약서 키 순서로 복원
            "evidence": _EVIDENCE.dump_python(_EVIDENCE.validate_python(json.loads(r["evidence_json"])), by_alias=True),
            "proposal": r["proposal_text"], "steps": json.loads(r["steps_json"]),
            "measurement": Measurement.model_validate(json.loads(r["measurement_json"])).model_dump(by_alias=True),
            "decision": {"status": r["decision_status"], "note": r["decision_note"], "decidedAt": iso(r["decided_at"])},
            "createdAt": iso(r["created_at"])}


def _in(ids: list[int]) -> str:
    return ",".join(["%s"] * len(ids))


def messages(where: str, args: tuple) -> list[dict]:
    """메시지 + toolCalls(seq 오름차순) + proposals + usage(llm_usage 합산)."""
    rows = db.q(f"SELECT * FROM messages WHERE {where} ORDER BY created_at, id", args)
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    tcs, props, usage = {}, {}, {}
    for t in db.q(f"SELECT * FROM tool_calls WHERE message_id IN ({_in(ids)}) ORDER BY seq", ids):
        tcs.setdefault(t["message_id"], []).append(tool_call_dict(t))
    for p in db.q(f"SELECT * FROM proposals WHERE message_id IN ({_in(ids)}) ORDER BY seq", ids):
        props.setdefault(p["message_id"], []).append(proposal_dict(p))
    for u in db.q(f"""SELECT message_id, MIN(model) AS model, SUM(input_tokens) AS i, SUM(output_tokens) AS o,
                      SUM(cost_usd) AS c FROM llm_usage WHERE message_id IN ({_in(ids)}) AND purpose = 'agent'
                      GROUP BY message_id""", ids):
        usage[u["message_id"]] = {"model": u["model"], "inputTokens": int(u["i"]), "outputTokens": int(u["o"]),
                                  "costUsd": float(u["c"])}
    out = []
    for r in rows:
        running = r["status"] == "running"
        out.append({"id": r["id"], "conversationId": r["conversation_id"], "role": r["role"], "status": r["status"],
                    "content": "" if running else r["content"], "errorCode": r["error_code"],
                    "toolCalls": tcs.get(r["id"], []),
                    "proposals": [] if running else props.get(r["id"], []),
                    "usage": None if (running or r["role"] == "user") else usage.get(r["id"]),
                    "createdAt": iso(r["created_at"])})
    return out


def message(message_id: int) -> dict:
    return messages("id = %s", (message_id,))[0]


def _conv_or_404(conversation_id: int) -> dict:
    row = db.one("SELECT * FROM conversations WHERE id = %s", (conversation_id,))
    if row is None:
        raise ApiError(404, "CONVERSATION_NOT_FOUND", f"대화 {conversation_id}을 찾을 수 없습니다.")
    return row


@router.get("/conversations")
def list_conversations():
    # ponytail: 페이지네이션 없음, 사용자 2명이라 충분
    return {"items": [_summary(r) for r in db.q(SUMMARY_SQL + " ORDER BY c.updated_at DESC, c.id DESC")]}


@router.post("/conversations", status_code=201)
def create_conversation(body: CreateConversationIn | None = Body(default=None)):
    cid = db.x("INSERT INTO conversations (title) VALUES (%s)", (body.title if body else None,))
    return _summary(db.one(SUMMARY_SQL + " WHERE c.id = %s", (cid,)))


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int):
    c = _conv_or_404(conversation_id)
    return {"id": c["id"], "title": c["title"], "createdAt": iso(c["created_at"]), "updatedAt": iso(c["updated_at"]),
            "messages": messages("conversation_id = %s", (conversation_id,))}


@router.patch("/proposals/{proposal_id}")
def patch_proposal(proposal_id: int, body: PatchProposalIn):
    p = db.one("SELECT * FROM proposals WHERE id = %s", (proposal_id,))
    if p is None:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", f"제안 {proposal_id}을 찾을 수 없습니다.")
    note = body.note if "note" in body.model_fields_set else p["decision_note"]  # 키 생략 → 기존 메모 유지
    if body.status == "pending":
        decided = "NULL"
    elif body.status != p["decision_status"]:
        decided = "NOW(3)"
    else:
        decided = "decided_at"  # 같은 status 재요청이면 결정 시각 유지
    db.x(f"UPDATE proposals SET decision_status = %s, decision_note = %s, decided_at = {decided} WHERE id = %s",
         (body.status, note, proposal_id))
    db.x("UPDATE conversations SET updated_at = NOW(3) WHERE id = %s", (p["conversation_id"],))
    return proposal_dict(db.one("SELECT * FROM proposals WHERE id = %s", (proposal_id,)))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _fail(mid: int, code: str) -> None:
    db.x("UPDATE messages SET status = 'failed', error_code = %s WHERE id = %s AND status = 'running'", (code, mid))
    db.x("UPDATE tool_calls SET status = 'failed' WHERE message_id = %s AND status = 'running'", (mid,))


def fail_stale_runs() -> None:
    """기동 시 이전 프로세스에서 끊긴 실행 마감. 단일 워커라 running 상태는 모두 고아."""
    for r in db.q("SELECT id FROM messages WHERE status = 'running'"):
        _fail(r["id"], "INTERNAL_ERROR")


@router.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: int, body: SendMessageIn):
    c = _conv_or_404(conversation_id)
    if db.one("SELECT id FROM messages WHERE conversation_id = %s AND status = 'running'", (conversation_id,)):
        raise ApiError(409, "RUN_IN_PROGRESS", "이 대화에서 이미 에이전트가 실행 중입니다. 끝난 뒤 다시 보내 주세요.")
    budget.check()
    # ponytail: 확인과 삽입 사이 경쟁 미방지(사용자 2명). 필요하면 conversations 행 SELECT ... FOR UPDATE
    uid = db.x("INSERT INTO messages (conversation_id, role, status, content) VALUES (%s, 'user', 'completed', %s)",
               (conversation_id, body.content))
    if c["title"] is None:
        db.x("UPDATE conversations SET title = %s WHERE id = %s", (body.content[:40], conversation_id))
    aid = db.x("INSERT INTO messages (conversation_id, role, status, content) VALUES (%s, 'assistant', 'running', '')",
               (conversation_id,))
    db.x("UPDATE conversations SET updated_at = NOW(3) WHERE id = %s", (conversation_id,))
    created = {"userMessage": message(uid), "assistantMessageId": aid}
    return StreamingResponse(_stream(aid, conversation_id, body.content, created), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def _stream(aid: int, conversation_id: int, content: str, created: dict):
    queue: asyncio.Queue = asyncio.Queue()

    async def pump():
        try:
            async for ev in agent.run_agent(aid, conversation_id, content):
                await queue.put(ev)
        except Exception:
            log.exception("agent run failed")
            await queue.put({"type": "error", "code": "INTERNAL_ERROR", "message": "에이전트 실행 중 서버 오류가 발생했습니다."})

    task = asyncio.create_task(pump())
    calls: dict[str, tuple[int, float]] = {}  # 이벤트 key → (tool_calls.id, 시작 monotonic)
    finished = False
    try:
        yield _sse("message_created", created)
        while True:
            try:
                ev = await asyncio.wait_for(queue.get(), PING_SECONDS)
            except TimeoutError:
                yield ": ping\n\n"
                continue
            try:
                kind = ev["type"]
                if kind == "tool_call":
                    seq = len(calls) + 1
                    tid = db.x("""INSERT INTO tool_calls (message_id, seq, source, name, input_json, status)
                                  VALUES (%s, %s, %s, %s, %s, 'running')""",
                               (aid, seq, ev["source"], ev["name"][:100], json.dumps(ev["input"], ensure_ascii=False)))
                    calls[ev["key"]] = (tid, time.monotonic())
                    yield _sse("tool_call", tool_call_dict(db.one("SELECT * FROM tool_calls WHERE id = %s", (tid,))))
                elif kind == "tool_result":
                    tid, t0 = calls[ev["key"]]
                    db.x("UPDATE tool_calls SET status = %s, result_summary = %s, result_text = %s, duration_ms = %s WHERE id = %s",
                         (ev["status"], (ev["summary"] or "")[:500], ev.get("text"), int((time.monotonic() - t0) * 1000), tid))
                    yield _sse("tool_result", tool_call_dict(db.one("SELECT * FROM tool_calls WHERE id = %s", (tid,))))
                elif kind == "final":
                    for i, p in enumerate(ev["proposals"], 1):
                        db.x("""INSERT INTO proposals (message_id, conversation_id, seq, type, title, evidence_json, proposal_text,
                                steps_json, measurement_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                             (aid, conversation_id, i, p["type"], p["title"], json.dumps(p["evidence"], ensure_ascii=False),
                              p["proposal"], json.dumps(p["steps"], ensure_ascii=False),
                              json.dumps(p["measurement"], ensure_ascii=False)))
                    db.x("""UPDATE tool_calls SET status = 'failed', result_summary = '실행 상한으로 중단됨'
                            WHERE message_id = %s AND status = 'running'""", (aid,))  # 시간 상한으로 끊긴 호출
                    db.x("UPDATE messages SET status = 'completed', content = %s WHERE id = %s", (ev["content"], aid))
                    db.x("UPDATE conversations SET updated_at = NOW(3) WHERE id = %s", (conversation_id,))
                    finished = True
                    yield _sse("final", message(aid))
                    return
                else:
                    _fail(aid, ev["code"])
                    db.x("UPDATE conversations SET updated_at = NOW(3) WHERE id = %s", (conversation_id,))
                    finished = True
                    yield _sse("error", {"error": {"code": ev["code"], "message": ev["message"]}, "assistantMessageId": aid})
                    return
            except Exception:  # 저장 실패도 error 이벤트 하나로 종료
                log.exception("stream handling failed")
                _fail(aid, "INTERNAL_ERROR")
                finished = True
                yield _sse("error", {"error": {"code": "INTERNAL_ERROR", "message": "실행 결과 저장 중 서버 오류가 발생했습니다."},
                                     "assistantMessageId": aid})
                return
    finally:
        task.cancel()
        if not finished:  # 클라이언트 연결 끊김
            _fail(aid, "INTERNAL_ERROR")
