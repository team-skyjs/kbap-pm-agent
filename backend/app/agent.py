"""외부 seam: 모든 LLM 호출. run_agent(에이전트 실행 → 내부 이벤트)와 summarize(코드 요약).
내부 이벤트(dict):
  {"type": "tool_call", "key", "source", "name", "input"}
  {"type": "tool_result", "key", "status": "succeeded"|"failed", "summary", "text"}
  {"type": "final", "content", "proposals": [ProposalDraft 별칭 dict]}
  {"type": "error", "code", "message"}
DB 저장과 SSE 변환은 conversations.py가 한다."""
import asyncio
import datetime
import logging
from typing import AsyncIterator

from app import budget, db
from app.config import env, is_fake, num

log = logging.getLogger("app.agent")

# 계약서 v1.1 예시 값 (시연 모드 표: 도구 2개 taxonomy·code, 제안 improvement 1 + funnel_design 1)
FAKE_TOOLS = [
    ("taxonomy", "search_taxonomy", {"query": "cart"}, "일치 이벤트 2개: cart_add, cart_view"),
    ("code", "find_event_calls", {"eventName": "scan_complete"}, "2곳: src/app/scan.tsx:405 (실패), src/app/scan.tsx:427 (성공)"),
]
FAKE_CONTENT = ("지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다. "
                "실패의 62%가 OCR 실패이고, 실패 화면에 재시도 동작이 없습니다. 아래 두 제안을 확인해 주세요.")
FAKE_PROPOSALS = [
    {"type": "improvement", "title": "OCR 실패 화면에 재시도·직접 입력 동선 추가",
     "evidence": [{"kind": "metric", "summary": "실패한 scan_complete 중 fail_reason=ocr_empty가 62%다.", "value": "62%",
                   "source": "Amplitude segmentation: scan_complete(success=false) by fail_reason, 2026-09-15~2026-10-14"}],
     "proposal": "OCR 실패 화면에 '다시 찍기'와 '메뉴 이름 직접 입력' 버튼을 둔다.",
     "steps": ["src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.", "직접 입력은 기존 search 화면으로 이동시킨다."],
     "measurement": {"primaryMetric": "scan_start 대비 scan_complete(success=true) 전환율", "baseline": "41.3%",
                     "target": "48%", "funnel": []}},
    {"type": "funnel_design", "title": "스캔 실패 후 재시도 퍼널 측정 설계",
     "evidence": [
         {"kind": "metric", "summary": "최근 30일 scan_start 대비 성공한 scan_complete 전환율이 41.3%다.", "value": "41.3%",
          "source": "Amplitude funnel: scan_start → scan_complete(success=true), 2026-09-15~2026-10-14"},
         {"kind": "code", "summary": "실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다.",
          "file": "src/app/scan.tsx", "function": "onScanFailed", "line": 405,
          "snippet": "track(EVENTS.scan_complete, { success: false, fail_reason: reason, item_count: 0, degraded: false });"},
         {"kind": "taxonomy", "summary": "scan_complete는 성공·실패를 success 속성으로 구분한다.", "eventName": "scan_complete"}],
     "proposal": "실패 화면의 재시도 동작에 신규 이벤트 scan_retry_tap을 심어, 실패 후 재시도로 회복되는 비율을 측정한다.",
     "steps": ["EVENTS 상수에 scan_retry_tap을 추가한다.",
               "src/app/scan.tsx의 handleRetry 첫 줄에서 track(EVENTS.scan_retry_tap, { fail_reason })를 호출한다.",
               "택사노미 문서에 scan_retry_tap 정의와 fail_reason 속성을 추가한다.",
               "배포 후 7일간 아래 퍼널을 Amplitude에 저장해 확인한다."],
     "measurement": {
         "primaryMetric": "scan_complete(success=false) 이후 24시간 내 scan_complete(success=true) 도달 비율",
         "baseline": None, "target": "35%",
         "funnel": [
             {"order": 1, "eventName": "scan_complete", "status": "existing", "condition": "success=false", "location": None, "properties": []},
             {"order": 2, "eventName": "scan_retry_tap", "status": "new", "condition": None,
              "location": {"file": "src/app/scan.tsx", "function": "handleRetry", "line": 398},
              "properties": [{"name": "fail_reason", "type": "string"}]},
             {"order": 3, "eventName": "scan_complete", "status": "existing", "condition": "success=true", "location": None, "properties": []}]}},
]


def agent_model() -> str:
    return env("AGENT_MODEL") or "fake"


async def _fake(message_id: int) -> AsyncIterator[dict]:
    delay = num("FAKE_DELAY_SECONDS", 0.5)
    for i, (source, name, args, summary) in enumerate(FAKE_TOOLS):
        await asyncio.sleep(delay)
        yield {"type": "tool_call", "key": str(i), "source": source, "name": name, "input": args}
        await asyncio.sleep(delay)
        yield {"type": "tool_result", "key": str(i), "status": "succeeded", "summary": summary, "text": summary}
    await asyncio.sleep(delay)
    budget.record("agent", agent_model(), 0, 0, message_id)
    yield {"type": "final", "content": FAKE_CONTENT, "proposals": FAKE_PROPOSALS}


SYSTEM_PROMPT = """너는 K-Bap 앱 팀의 PM 에이전트다. PM 질문에 답하려고 택사노미, 프론트엔드 코드, Amplitude 지표를 도구로 여러 번 조회하고, 중간 결과를 보고 다음 조회를 정한다.

최종 응답은 반드시 AgentAnswer 구조로 낸다.
- content: 한국어 마크다운. 찾은 것을 짧게 요약한다. 제안 내용을 여기에 섞지 않는다.
- proposals: 제안 0개 이상. 기획 개선이면 type "improvement", 측정 설계면 type "funnel_design".

제안 규칙:
1. 제안은 반드시 근거(evidence) → 제안(proposal) → 실행 단계(steps) → 측정 방법(measurement) 네 부분이다.
2. 근거는 kind로 구분한다. metric은 Amplitude 수치(value에 단위, source에 조회 조건), code는 코드 위치(file은 저장소 루트 기준 경로, function은 감싸는 함수·컴포넌트 이름, line, snippet 10줄 이내), taxonomy는 이벤트 정의(eventName). 도구로 확인한 사실만 근거로 쓴다. 수치를 지어내지 않는다.
3. 측정 퍼널의 각 단계는 기존 이벤트(status "existing", location null)인지 신규 이벤트(status "new")인지 표시한다. 신규 이벤트는 location(file, function, line)이 필수이고, 도구로 실제 존재를 확인한 파일·함수만 쓴다. order는 1부터 연속이다. funnel_design은 퍼널이 1단계 이상이어야 한다.
4. 택사노미에 정의는 있으나 코드에서 호출을 찾지 못한 이벤트는 근거 summary에 "정의는 있으나 코드에서 발견되지 않음"이라고 쓴다. 코드에만 있고 택사노미 정의가 없는 이벤트는 "코드에만 존재, 정의 없음"이라고 쓴다.
5. 쓸 수 없는 소스(아래 상태가 '없음'이거나 도구 호출이 실패한 소스)가 있으면 content에 어떤 근거가 빠졌는지 명시한다.
6. 코드는 find_event_calls, search_code로 위치를 좁힌 뒤 read_code로 필요한 줄만 읽는다. 파일 전체를 읽으려 하지 않는다.
"""


def _model():
    from langchain.chat_models import init_chat_model
    return init_chat_model(agent_model(), max_tokens=16000)


async def _tools():
    """(도구 목록, 이름 → source, 소스 상태 문장). 쓸 수 있는 소스의 도구만 넣는다."""
    from app import amplitude, code_tools, repo
    tools, source = [], {}
    has_code = bool(repo.state()) and repo.clone_dir().exists()
    has_tax = bool(db.get_setting("taxonomy"))
    if has_code:
        tools += code_tools.CODE_TOOLS
        source.update({f.__name__: "code" for f in code_tools.CODE_TOOLS})
    if has_tax:
        tools += code_tools.TAXONOMY_TOOLS
        source.update({f.__name__: "taxonomy" for f in code_tools.TAXONOMY_TOOLS})
    amp = "없음(연결 안 됨)"
    try:
        amp_tools = await amplitude.tools()
        if amp_tools:
            tools += amp_tools
            source.update({t.name: "amplitude" for t in amp_tools})
            amp = "있음"
    except Exception as e:  # Amplitude가 막혀도 나머지 소스로 답한다(US1-4)
        log.warning("amplitude tools unavailable: %s", e)
        amp = "없음(연결 실패)"
    status = f"소스 상태: 코드 저장소 {'있음' if has_code else '없음'}, 택사노미 {'있음' if has_tax else '없음'}, Amplitude {amp}"
    return tools, source, status


def _history(conversation_id: int) -> list[dict]:
    # ponytail: 최근 완료 메시지 20개를 본문만 넣는다(도구 결과 원문 제외). 긴 대화는 요약 압축으로
    rows = db.q("""SELECT role, content FROM messages WHERE conversation_id = %s AND status = 'completed'
                   ORDER BY created_at DESC, id DESC LIMIT 20""", (conversation_id,))
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows) if r["content"]]


def partial_content(reason: str, results: list[tuple[str, str]]) -> str:
    lines = [reason, "", "조회 결과:"] + [f"- {name}: {summary}" for name, summary in results]
    return "\n".join(lines if results else [reason, "", "조회한 결과가 없습니다."])


async def _real(message_id: int, conversation_id: int) -> AsyncIterator[dict]:
    from langchain.agents import create_agent
    from langchain.agents.middleware import ToolErrorMiddleware
    from langchain.agents.structured_output import ProviderStrategy

    from app.schemas import AgentAnswer

    tools, source, status = await _tools()
    max_calls, timeout = int(num("AGENT_MAX_TOOL_CALLS", 20)), num("AGENT_TIMEOUT_SECONDS", 170)
    results: list[tuple[str, str]] = []  # (도구 이름, 결과 요약) — 상한 도달 시 부분 답에 쓴다
    names: dict[str, str] = {}
    calls, answer, reason = 0, None, None
    try:
        # ToolStrategy는 tool_choice "any"를 강제해 최신 Claude 모델에서 400이다. 공급자 네이티브 구조화 출력을 쓴다
        graph = create_agent(
            _model(), tools,
            system_prompt=f"{SYSTEM_PROMPT}\n오늘 날짜(UTC): {datetime.date.today().isoformat()}\n{status}",
            response_format=ProviderStrategy(AgentAnswer),
            middleware=[ToolErrorMiddleware(on_error=lambda e, _req: f"도구 오류: {type(e).__name__}: {str(e)[:300]}")])
        async with asyncio.timeout(timeout):
            async for chunk in graph.astream({"messages": _history(conversation_id)}, stream_mode="updates"):
                for node, update in (chunk or {}).items():
                    update = update or {}
                    for msg in update.get("messages", []):
                        if msg.type == "ai":
                            u = msg.usage_metadata or {}
                            budget.record("agent", agent_model(), u.get("input_tokens", 0), u.get("output_tokens", 0), message_id)
                            for tc in msg.tool_calls:
                                if tc["name"] not in source:
                                    continue
                                calls += 1
                                names[tc["id"]] = tc["name"]
                                yield {"type": "tool_call", "key": tc["id"], "source": source[tc["name"]],
                                       "name": tc["name"], "input": tc["args"]}
                        elif msg.type == "tool" and msg.tool_call_id in names:
                            text = msg.content if isinstance(msg.content, str) else "\n".join(
                                b.get("text", "") if isinstance(b, dict) else str(b) for b in msg.content)  # MCP 결과는 블록 목록
                            failed = getattr(msg, "status", "success") == "error"
                            summary = text.splitlines()[0][:500] if text else ""
                            results.append((names[msg.tool_call_id], summary))
                            yield {"type": "tool_result", "key": msg.tool_call_id,
                                   "status": "failed" if failed else "succeeded", "summary": summary, "text": text}
                    if update.get("structured_response") is not None:
                        answer = update["structured_response"]
                if calls >= max_calls and len(results) >= calls and answer is None:  # 걸린 호출의 결과까지 받은 뒤 멈춘다
                    reason = f"도구 호출 상한({max_calls}회)에 도달해 여기까지의 조회 결과로 답합니다."
                    break
    except TimeoutError:
        reason = f"실행 시간 상한({timeout:g}초)에 도달해 여기까지의 조회 결과로 답합니다."
    except Exception as e:
        log.exception("model call failed")
        yield {"type": "error", "code": "UPSTREAM_ERROR", "message": f"LLM 공급자 응답 오류로 실행을 중단했습니다. ({type(e).__name__})"}
        return
    if answer is not None:
        yield {"type": "final", "content": answer.content,
               "proposals": [p.model_dump(by_alias=True) for p in answer.proposals]}
    elif reason:
        yield {"type": "final", "content": partial_content(reason, results), "proposals": []}
    else:
        yield {"type": "error", "code": "UPSTREAM_ERROR", "message": "모델이 구조화된 최종 응답을 내지 않았습니다."}


async def run_agent(message_id: int, conversation_id: int, content: str) -> AsyncIterator[dict]:
    source = _fake(message_id) if is_fake() else _real(message_id, conversation_id)
    async for ev in source:
        yield ev


SUMMARY_PROMPT = ("다음은 React Native 화면 파일이다. 150단어 이내 한국어로 요약하라: 화면의 역할, 주요 컴포넌트, "
                  "사용자 동작 핸들러 이름, 보내는 분석 이벤트(track 호출) 이름. 추측하지 말고 코드에 있는 것만.\n\n")


def summarize(text: str) -> str:
    """코드 요약 seam (CODE_SUMMARY_MODEL). 호출 전 budget.check()는 호출자가 한다."""
    model_name = env("CODE_SUMMARY_MODEL") or "fake"
    if is_fake():
        budget.record("code_summary", model_name, 0, 0, None)
        return "시연 모드 요약: 화면 역할·컴포넌트·핸들러·이벤트."
    from langchain.chat_models import init_chat_model
    resp = init_chat_model(model_name).invoke(SUMMARY_PROMPT + text)
    u = resp.usage_metadata or {}
    budget.record("code_summary", model_name, u.get("input_tokens", 0), u.get("output_tokens", 0), None)
    return resp.text if isinstance(resp.text, str) else str(resp.content)
