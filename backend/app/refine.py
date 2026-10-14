"""질문 다듬기 라우트: 보내기 전 질문을 한 번 다듬고, 사용자가 무엇을 골랐는지 기록."""
import logging

from fastapi import APIRouter

from app import agent, budget, db
from app.db import iso
from app.errors import ApiError
from app.schemas import RefineChoiceIn, RefineIn

log = logging.getLogger("app.refine")
router = APIRouter(prefix="/api/questions")
HISTORY_CHARS = 500
HISTORY_PER_ROLE = 2

REFINE_PROMPT = """너는 PM이 분석 에이전트에게 보낼 질문을 보내기 전에 다듬는 도우미다. 질문을 답하기 좋은 모양으로 고쳐 쓴다.

규칙:
1. 사용자의 의도를 바꾸지 않는다.
2. 기간, 대상 이벤트(아래 목록에 있는 실제 이름만), 보고 싶은 지표, 원하는 산출물(개선안인지 측정 설계인지)을 드러낸다.
3. 목록에 없는 이벤트 이름이나 원문에 없는 사실을 지어내지 않는다. 대상이 목록에 없으면 사용자의 말을 그대로 둔다.
4. 정보가 없으면 합리적 기본값(예: 최근 7일)을 쓰되 요약에 "(원문에 없음)"으로 밝힌다.
5. 이미 구체적이면 거의 그대로 두고 요약에 그렇게 적는다.
6. 개선안은 한국어 두 문장 이내, 요약은 한 줄이다."""


def _history(conversation_id: int) -> list[dict]:
    """완료된 비어 있지 않은 메시지 중 역할별 최근 2개, 오래된 순."""
    rows = []
    for role in ("user", "assistant"):
        rows += db.q("""SELECT id, role, content, created_at FROM messages
                        WHERE conversation_id = %s AND role = %s AND status = 'completed' AND content <> ''
                        ORDER BY created_at DESC, id DESC LIMIT %s""", (conversation_id, role, HISTORY_PER_ROLE))
    return sorted(rows, key=lambda r: (r["created_at"], r["id"]))


def build_prompt(question: str, conversation_id: int | None) -> str:
    """규칙 + 택사노미 이벤트 이름(정의·속성 없이) + 최근 대화 + 질문 + 출력 형식."""
    t = db.get_setting("taxonomy")
    names = ", ".join(e["name"] for e in t["events"]) if t and t.get("events") else "택사노미 없음"
    rows = _history(conversation_id) if conversation_id is not None else []
    history = "\n".join(f"[{'사용자' if r['role'] == 'user' else '에이전트'}] {r['content'][:HISTORY_CHARS]}"
                        for r in rows) or "이력 없음"
    return (f"{REFINE_PROMPT}\n\n## 택사노미 이벤트 이름\n{names}\n\n## 직전 대화(오래된 순)\n{history}"
            f"\n\n## 다듬을 질문\n{question}\n\n## 출력\nrefined: 다듬은 질문. summary: 무엇이 달라졌는지 한 줄.")


@router.post("/refine")
async def refine_question(body: RefineIn):
    if body.conversation_id is not None and not db.one("SELECT id FROM conversations WHERE id = %s",
                                                       (body.conversation_id,)):
        raise ApiError(404, "CONVERSATION_NOT_FOUND", f"대화 {body.conversation_id}을 찾을 수 없습니다.")
    budget.check()
    try:
        result, model = await agent.refine(build_prompt(body.question, body.conversation_id))
    except Exception as e:
        # ponytail: 응답 파싱 단계에서 실패하면 그 호출의 토큰은 기록되지 않음. 실패가 잦으면 런타임에서 usage를 먼저 기록
        log.warning("refine failed: %s", type(e).__name__)
        raise ApiError(502, "UPSTREAM_ERROR", "질문 다듬기 모델 호출에 실패했습니다. 원문으로 보내거나 다시 시도해 주세요.")
    rid = db.x("""INSERT INTO question_refinements (conversation_id, original_question, refined_question, summary, model)
                  VALUES (%s, %s, %s, %s, %s)""",
               (body.conversation_id, body.question, result.refined, result.summary, model))
    return {"refinementId": rid, "refined": result.refined, "summary": result.summary}


@router.post("/refine/{refinement_id}/choice")
def record_choice(refinement_id: int, body: RefineChoiceIn):
    if not db.one("SELECT id FROM question_refinements WHERE id = %s", (refinement_id,)):
        raise ApiError(404, "REFINEMENT_NOT_FOUND", f"질문 다듬기 기록 {refinement_id}을 찾을 수 없습니다.")
    db.x("UPDATE question_refinements SET choice = %s, chosen_at = NOW(3) WHERE id = %s", (body.choice, refinement_id))
    r = db.one("SELECT id, choice, chosen_at FROM question_refinements WHERE id = %s", (refinement_id,))
    return {"refinementId": r["id"], "choice": r["choice"], "chosenAt": iso(r["chosen_at"])}
