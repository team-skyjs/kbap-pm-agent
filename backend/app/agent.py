"""외부 seam: 모든 LLM 호출. run_agent(에이전트 실행 → 내부 이벤트)와 summarize(코드 요약).
내부 이벤트(dict):
  {"type": "tool_call", "key", "source", "name", "input"}
  {"type": "tool_result", "key", "status": "succeeded"|"failed", "summary", "text"}
  {"type": "final", "content", "proposals": [ProposalDraft 별칭 dict]}
  {"type": "error", "code", "message"}
DB 저장과 SSE 변환은 conversations.py 담당."""
import asyncio
import datetime
import logging
from typing import AsyncIterator

import functools
import inspect
import uuid

from app import budget, db
from app.config import env, is_fake, num

log = logging.getLogger("app.agent")

# 계약서 예시 값: 도구 2개(taxonomy·code), 제안 improvement 1 + funnel_design 1
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
7. Amplitude 도구는 조회에만 쓴다. 차트를 만들거나 수정·저장하지 않는다.
8. Amplitude 조회는 필요한 범위만 요청한다. 시계열은 timeSeriesLimit로 최근 구간만, groupByLimit은 작게, includeAdditionalInfo는 끈다.
9. 마크다운 굵게(**) 바로 뒤에 조사를 붙이지 말고 한 칸 띄어 쓴다. 예: "**41.3%** 로", "**scan_complete** 이벤트".
10. 시계열 지표(날짜별 수치)를 답할 때는 본문에 chart 코드 블록을 함께 쓴다. 형식:
```chart
{"type":"line","title":"최근 7일 스캔 시작 사용자 수","x":["10-09","10-10","10-11","10-12","10-13","10-14","10-15"],"series":[{"name":"scan_start","values":[312,298,341,355,330,362,371]}]}
```
"""


# --- 런타임 선택: 모델 문자열 접두사 → 공급자 SDK 파일. 구현 두 개라 인터페이스 클래스 없이 dict 하나
def _runtimes() -> dict:
    from app import agent_anthropic, agent_openai
    return {"anthropic": agent_anthropic, "openai": agent_openai}


def runtime(model: str):
    """'provider:model' → (런타임 모듈, 모델 이름). 모르는 접두사는 ValueError."""
    provider, _, name = model.partition(":")
    mod = _runtimes().get(provider)
    if mod is None or not name:
        raise ValueError(f"지원하지 않는 모델 문자열입니다: {model!r} (anthropic:<모델> 또는 openai:<모델>)")
    return mod, name


def check_models() -> None:
    """기동 시 호출. real 모드에서 AGENT_MODEL·CODE_SUMMARY_MODEL 접두사가 틀리면 기동 실패."""
    if not is_fake():
        runtime(agent_model())
        runtime(env("CODE_SUMMARY_MODEL"))


class Refused(Exception):
    """모델의 stop_reason refusal 거절."""


class TurnLimit(Exception):
    """모델 호출 턴 상한(AGENT_MAX_TURNS) 도달. 각 런타임이 SDK 상한에 닿으면 발생."""


def max_turns() -> int:
    """실행 1회의 모델 호출(요청) 수 상한. 도구 호출은 비용 0이라 미포함. 병렬 도구 호출 응답도 1턴."""
    return int(num("AGENT_MAX_TURNS", 10))


def clip(text: str) -> str:
    """모델에 넘길 도구 결과 사본을 TOOL_RESULT_MAX_CHARS로 자르기. 이벤트·DB에는 원문 유지.
    큰 조회 결과가 매 턴 입력으로 반복 전송되어 토큰이 불어나는 것 방지."""
    limit = int(num("TOOL_RESULT_MAX_CHARS", 3000))
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n…({len(text)}자 중 {limit}자, 이하 생략)"


def wrap(fn, emit, source: str, name: str | None = None):
    """공통 도구 래퍼: tool_call 이벤트 → 실행 → tool_result 이벤트. 예외는 failed로 알린 뒤 다시 던져
    각 SDK가 오류 결과로 모델에 반환(도구 하나가 실패해도 실행 계속). functools.wraps로 원래 시그니처·docstring을
    도구 스키마의 원천으로 유지(MCP 도구는 런타임이 스키마를 따로 전달)."""
    tool_name = name or fn.__name__
    sig = inspect.signature(fn)
    is_async = inspect.iscoroutinefunction(fn)

    @functools.wraps(fn)
    async def tool(*args, **kwargs):
        args_in = {}
        for k, v in sig.bind(*args, **kwargs).arguments.items():  # **kwargs 매개변수(MCP 도구)는 펼침
            args_in.update(v) if sig.parameters[k].kind is inspect.Parameter.VAR_KEYWORD else args_in.__setitem__(k, v)
        key = uuid.uuid4().hex
        await emit({"type": "tool_call", "key": key, "source": source, "name": tool_name, "input": args_in})
        try:
            # 동기 코드 도구(rg·파일)는 스레드에서 실행, 이벤트 루프 차단 방지
            out = await fn(*args, **kwargs) if is_async else await asyncio.to_thread(fn, *args, **kwargs)
            text = out if isinstance(out, str) else str(out)
        except Exception as e:
            msg = f"도구 오류: {type(e).__name__}: {str(e)[:300]}"
            await emit({"type": "tool_result", "key": key, "status": "failed", "summary": msg, "text": msg})
            raise
        await emit({"type": "tool_result", "key": key, "status": "succeeded",
                    "summary": text.splitlines()[0][:500] if text else "", "text": text})
        return clip(text)

    return tool


def _code_tools() -> tuple[list[tuple], str]:
    """[(함수, source)]와 소스 상태 문장. 쓸 수 있는 소스의 도구만."""
    from app import code_tools, repo
    has_code = bool(repo.state()) and repo.clone_dir().exists()
    has_tax = bool(db.get_setting("taxonomy"))
    tools = ([(f, "code") for f in code_tools.CODE_TOOLS] if has_code else []) + \
            ([(f, "taxonomy") for f in code_tools.TAXONOMY_TOOLS] if has_tax else [])
    return tools, f"소스 상태: 코드 저장소 {'있음' if has_code else '없음'}, 택사노미 {'있음' if has_tax else '없음'}"


def _history(conversation_id: int) -> list[dict]:
    # ponytail: 최근 완료 메시지 20개의 본문만 전달(도구 결과 원문 제외). 긴 대화는 요약 압축으로
    rows = db.q("""SELECT role, content FROM messages WHERE conversation_id = %s AND status = 'completed'
                   ORDER BY created_at DESC, id DESC LIMIT 20""", (conversation_id,))
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows) if r["content"]]


def partial_content(reason: str, results: list[tuple[str, str]]) -> str:
    lines = [reason, "", "조회 결과:"] + [f"- {name}: {summary}" for name, summary in results]
    return "\n".join(lines if results else [reason, "", "조회한 결과가 없습니다."])


async def _real(message_id: int, conversation_id: int) -> AsyncIterator[dict]:
    from pydantic import ValidationError

    from app.schemas import AgentAnswer

    timeout = num("AGENT_TIMEOUT_SECONDS", 170)
    try:
        mod, model = runtime(agent_model())
    except ValueError as e:
        yield {"type": "error", "code": "UPSTREAM_ERROR", "message": str(e)}
        return
    queue: asyncio.Queue = asyncio.Queue()
    specs, status = _code_tools()
    tools = [wrap(f, queue.put, src) for f, src in specs]
    system = f"{SYSTEM_PROMPT}\n오늘 날짜(UTC): {datetime.date.today().isoformat()}\n{status}"

    def usage(input_tokens: int, output_tokens: int) -> None:
        budget.record("agent", agent_model(), input_tokens, output_tokens, message_id)

    task = asyncio.create_task(mod.run(model, system, _history(conversation_id), tools, queue.put, usage))
    results: list[tuple[str, str]] = []  # (도구 이름, 결과 요약), 상한 도달 시 부분 답에 사용
    names: dict[str, str] = {}
    reason = None
    try:
        async with asyncio.timeout(timeout):
            while True:
                getter = asyncio.ensure_future(queue.get())
                await asyncio.wait({getter, task}, return_when=asyncio.FIRST_COMPLETED)
                if not getter.done():
                    getter.cancel()
                    if queue.empty():
                        break  # 런타임 종료, 남은 이벤트 없음
                    ev = queue.get_nowait()
                else:
                    ev = getter.result()
                if ev["type"] == "tool_call":
                    names[ev["key"]] = ev["name"]
                elif ev["type"] == "tool_result":
                    results.append((names.get(ev["key"], "?"), ev["summary"]))
                yield ev
    except TimeoutError:
        reason = f"실행 시간 상한({timeout:g}초)에 도달해 여기까지의 조회 결과로 답합니다."
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    if reason is None and task.done() and not task.cancelled() and isinstance(task.exception(), TurnLimit):
        # 턴은 SDK가 셈(anthropic max_iterations, openai max_turns: 둘 다 모델 요청 1회 = 1턴, 마지막 턴의 도구까지 실행 후 정지)
        reason = f"모델 호출 상한({max_turns()}턴)에 도달해 여기까지의 조회 결과로 답합니다."
    if reason:
        yield {"type": "final", "content": partial_content(reason, results), "proposals": []}
        return
    try:
        # ponytail: 재시도 없음. AgentAnswer 교차 규칙(new 단계 location, order 연속 등) 위반도 실행 전체가
        # UPSTREAM_ERROR/failed. 실제 실행에서 위반이 반복되면 검증 오류를 붙여 1회 재요청으로
        answer = AgentAnswer.model_validate_json(task.result())
    except Refused:
        yield {"type": "error", "code": "UPSTREAM_ERROR", "message": "모델이 요청을 거절해 실행을 중단했습니다."}
        return
    except ValidationError as e:
        log.warning("AgentAnswer validation failed: %s", e)
        yield {"type": "error", "code": "UPSTREAM_ERROR", "message": "모델 응답이 제안 구조 규칙을 어겨 실행을 중단했습니다."}
        return
    except Exception as e:
        log.exception("model call failed")
        yield {"type": "error", "code": "UPSTREAM_ERROR", "message": f"LLM 공급자 응답 오류로 실행을 중단했습니다. ({type(e).__name__})"}
        return
    yield {"type": "final", "content": answer.content, "proposals": [p.model_dump(by_alias=True) for p in answer.proposals]}


async def run_agent(message_id: int, conversation_id: int, content: str) -> AsyncIterator[dict]:
    source = _fake(message_id) if is_fake() else _real(message_id, conversation_id)
    async for ev in source:
        yield ev


SUMMARY_PROMPT = ("다음은 React Native 화면 파일이다. 150단어 이내 한국어로 요약하라: 화면의 역할, 주요 컴포넌트, "
                  "사용자 동작 핸들러 이름, 보내는 분석 이벤트(track 호출) 이름. 추측하지 말고 코드에 있는 것만.\n\n")


def summarize(text: str) -> str:
    """코드 요약 seam (CODE_SUMMARY_MODEL). 호출 전 budget.check()는 호출자 몫. 백그라운드 스레드에서 호출."""
    model_str = env("CODE_SUMMARY_MODEL") or "fake"
    if is_fake():
        budget.record("code_summary", model_str, 0, 0, None)
        return "시연 모드 요약: 화면 역할·컴포넌트·핸들러·이벤트."
    mod, name = runtime(model_str)
    out, input_tokens, output_tokens = asyncio.run(mod.summarize(name, SUMMARY_PROMPT + text))
    budget.record("code_summary", model_str, input_tokens, output_tokens, None)
    return out
