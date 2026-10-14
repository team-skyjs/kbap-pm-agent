"""질문 다듬기 라우트: 보내기 전 질문을 한 번 다듬고, 사용자가 무엇을 골랐는지 기록."""
import logging
import re

from fastapi import APIRouter

from app import agent, budget, db
from app.db import iso
from app.errors import ApiError
from app.schemas import RefineChoiceIn, RefineIn

log = logging.getLogger("app.refine")
router = APIRouter(prefix="/api/questions")
HISTORY_CHARS = 500
HISTORY_PER_ROLE = 2
NAMES_MAX_CHARS = 4000  # 이벤트 이름이 매우 많은 택사노미에서 입력 토큰 상한
TRUNCATED_NOTE = " (택사노미 이름이 많아 앞부분만 참고)"
SUMMARY_MAX = 300

REFINE_PROMPT = """너는 PM이 분석 에이전트에게 보낼 질문을 보내기 전에 다듬는 도우미다. 질문을 답하기 좋은 모양으로 고쳐 쓴다.

규칙:
1. 사용자의 의도를 바꾸지 않는다.
2. 기간, 대상 이벤트(아래 목록에 있는 실제 이름만), 보고 싶은 지표, 원하는 산출물(개선안인지 측정 설계인지)을 드러낸다.
3. 목록에 없는 이벤트 이름이나 원문에 없는 사실을 지어내지 않는다. 대상이 목록에 없으면 사용자의 말을 그대로 둔다.
4. 정보가 없으면 합리적 기본값(예: 최근 7일)을 쓰되 요약에 "(원문에 없음)"으로 밝힌다.
5. 이미 구체적이면 거의 그대로 두고 요약에 그렇게 적는다.
6. 개선안은 한국어 두 문장 이내, 요약은 한 줄이다.
7. 질문의 대상 이벤트가 택사노미에 없으면 대상을 바꾸지 말고 원문 표현을 유지하며, 요약에 '택사노미에 없는 이벤트'라고 적는다.
8. 기간·이벤트·지표·산출물이 이미 분명하면 문장을 거의 바꾸지 않고 요약에 '거의 그대로'라고 적는다. 없는 조건을 추가하지 않는다.
9. 개선된 질문은 4,000자 이내로 쓴다."""


def _history(conversation_id: int) -> list[dict]:
    """완료된 비어 있지 않은 메시지 중 역할별 최근 2개, 오래된 순."""
    rows = []
    for role in ("user", "assistant"):
        rows += db.q("""SELECT id, role, content, created_at FROM messages
                        WHERE conversation_id = %s AND role = %s AND status = 'completed' AND content <> ''
                        ORDER BY created_at DESC, id DESC LIMIT %s""", (conversation_id, role, HISTORY_PER_ROLE))
    return sorted(rows, key=lambda r: (r["created_at"], r["id"]))


def taxonomy_names() -> list[str]:
    t = db.get_setting("taxonomy")
    return [e["name"] for e in t["events"]] if t and t.get("events") else []


def cap_names(names: list[str], question: str = "") -> tuple[list[str], bool]:
    """쉼표로 이은 이름 문자열이 4,000자 안에 드는 이름까지만. (넣은 이름, 잘렸는가).
    넘칠 때만 질문과 겹치는 이름을 원래 순서로 먼저, 남는 자리는 나머지를 원래 순서로: 잘려도 물은 이벤트가 빠지지 않게.
    겹침 = 이름 전체가 질문에 있거나, 이름을 _로 나눈 조각 하나가 질문의 영숫자 낱말(소문자)과 같음"""
    if len(", ".join(names)) <= NAMES_MAX_CHARS:
        return names, False
    q = question.lower()
    words = set(re.findall(r"[a-z0-9]+", q))
    related = [n for n in names if n.lower() in q or any(p in words for p in n.lower().split("_") if p)]
    picked = set(related)
    kept, length = [], 0
    for n in related + [n for n in names if n not in picked]:
        length += len(n) + (2 if kept else 0)
        if length > NAMES_MAX_CHARS:
            return kept, True
        kept.append(n)
    return kept, True


def with_truncated_note(summary: str) -> str:
    """모델은 잘림을 모르므로 서버가 요약 끝에 표시. 300자를 넘으면 모델 요약 쪽을 줄임"""
    return summary.rstrip()[:SUMMARY_MAX - len(TRUNCATED_NOTE)] + TRUNCATED_NOTE


def render_prompt(question: str, names: list[str], rows: list[dict]) -> str:
    """규칙 + 택사노미 이벤트 이름(정의·속성 없이) + 최근 대화(rows: role·content, 오래된 순) + 질문 + 출력 형식."""
    history = "\n".join(f"[{'사용자' if r['role'] == 'user' else '에이전트'}] {r['content'][:HISTORY_CHARS]}"
                        for r in rows) or "이력 없음"
    return (f"{REFINE_PROMPT}\n\n## 택사노미 이벤트 이름\n{', '.join(names) or '택사노미 없음'}"
            f"\n\n## 직전 대화(오래된 순)\n{history}"
            f"\n\n## 다듬을 질문\n{question}\n\n## 출력\nrefined: 다듬은 질문. summary: 무엇이 달라졌는지 한 줄.")


def build_prompt(question: str, conversation_id: int | None) -> tuple[str, bool]:
    """(프롬프트, 택사노미 이름이 잘렸는가)"""
    rows = _history(conversation_id) if conversation_id is not None else []
    names, truncated = cap_names(taxonomy_names(), question)
    return render_prompt(question, names, rows), truncated


@router.post("/refine")
async def refine_question(body: RefineIn):
    if body.conversation_id is not None and not db.one("SELECT id FROM conversations WHERE id = %s",
                                                       (body.conversation_id,)):
        raise ApiError(404, "CONVERSATION_NOT_FOUND", f"대화 {body.conversation_id}을 찾을 수 없습니다.")
    budget.check()  # 유료 호출 전에 거절
    prompt, truncated = build_prompt(body.question, body.conversation_id)
    try:
        result, model = await agent.refine(prompt)
    except Exception as e:
        # ponytail: 응답 파싱 단계에서 실패하면 그 호출의 토큰은 기록되지 않음. 실패가 잦으면 런타임에서 usage를 먼저 기록
        log.warning("refine failed: %s", type(e).__name__)
        raise ApiError(502, "UPSTREAM_ERROR", "질문 다듬기 모델 호출에 실패했습니다. 원문으로 보내거나 다시 시도해 주세요.")
    summary = with_truncated_note(result.summary) if truncated else result.summary
    rid = db.x("""INSERT INTO question_refinements (conversation_id, original_question, refined_question, summary, model)
                  VALUES (%s, %s, %s, %s, %s)""",
               (body.conversation_id, body.question, result.refined, summary, model))
    return {"refinementId": rid, "refined": result.refined, "summary": summary}


@router.post("/refine/{refinement_id}/choice")
def record_choice(refinement_id: int, body: RefineChoiceIn):
    if not db.one("SELECT id FROM question_refinements WHERE id = %s", (refinement_id,)):
        raise ApiError(404, "REFINEMENT_NOT_FOUND", f"질문 다듬기 기록 {refinement_id}을 찾을 수 없습니다.")
    db.x("UPDATE question_refinements SET choice = %s, chosen_at = NOW(3) WHERE id = %s", (body.choice, refinement_id))
    r = db.one("SELECT id, choice, chosen_at FROM question_refinements WHERE id = %s", (refinement_id,))
    return {"refinementId": r["id"], "choice": r["choice"], "chosenAt": iso(r["chosen_at"])}
