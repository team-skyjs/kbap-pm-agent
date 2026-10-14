"""대화·메시지·제안 라우트 (contracts/04, 05, 06)."""
import json

from fastapi import APIRouter, Body

from app import db
from app.db import iso
from app.errors import ApiError
from app.schemas import CreateConversationIn, PatchProposalIn

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
            "type": r["type"], "title": r["title"], "evidence": json.loads(r["evidence_json"]),
            "proposal": r["proposal_text"], "steps": json.loads(r["steps_json"]),
            "measurement": json.loads(r["measurement_json"]),
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
    # ponytail: 페이지네이션 없음(사용자 2명, 계약서 공통 규칙)
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
        decided = "decided_at"  # 같은 status 재요청은 결정 시각을 바꾸지 않는다
    db.x(f"UPDATE proposals SET decision_status = %s, decision_note = %s, decided_at = {decided} WHERE id = %s",
         (body.status, note, proposal_id))
    db.x("UPDATE conversations SET updated_at = NOW(3) WHERE id = %s", (p["conversation_id"],))
    return proposal_dict(db.one("SELECT * FROM proposals WHERE id = %s", (proposal_id,)))
