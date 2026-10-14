"""OpenAI Agents SDK 런타임. 상한·이벤트·사용량 기록·사후 검증은 agent.py, 여기는 SDK 호출만."""
import json
import logging

from agents import Agent, MaxTurnsExceeded, OpenAIResponsesModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from app import amplitude

log = logging.getLogger("app.agent_openai")
# ponytail: SDK 기본 트레이싱이 실행 내용(코드 발췌·지표)을 OpenAI 트레이스로 전송. 외부 유출 방지를 위해 비활성
set_tracing_disabled(True)
FAIL = "도구 오류:"  # MCP 실패 결과 머리말, tool_result failed 판별용


def _client() -> AsyncOpenAI:
    """검사 스크립트가 가짜 전송(httpx.MockTransport)을 넣은 클라이언트로 교체."""
    return AsyncOpenAI()


def _model(name: str) -> OpenAIResponsesModel:
    return OpenAIResponsesModel(model=name, openai_client=_client())


def _mcp_failure(_ctx, error: Exception) -> str:
    return f"{FAIL} {type(error).__name__}: {str(error)[:300]}"


def _mcp_error_flag(ctx) -> dict:
    return {"is_error": bool(ctx.is_error)}  # MCP isError 결과는 예외가 아닌 일반 출력이라 별도 전달


def _text(output) -> str:
    """MCP 출력(내용 블록 dict 또는 목록)에서 사람이 읽을 텍스트만 추출."""
    blocks = output if isinstance(output, list) else [output]
    return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in blocks)


def _call_id(raw) -> str | None:
    return raw.get("call_id") if isinstance(raw, dict) else getattr(raw, "call_id", None)


async def run(model: str, system: str, history: list[dict], tools: list, emit, usage) -> str:
    """도구 루프 실행 후 최종 AgentAnswer JSON 문자열 반환."""
    from app.agent import TurnLimit, max_turns
    from app.schemas import AgentAnswer

    ftools = [function_tool(t) for t in tools]  # 이벤트는 공통 래퍼 담당
    fnames = {t.name for t in ftools}
    server, servers, amp = amplitude.openai_server(failure_error_function=_mcp_failure,
                                                                custom_data_extractor=_mcp_error_flag), [], "없음(연결 안 됨)"
    if server:
        try:
            await server.connect()
            if await server.list_tools():  # 허용 목록 적용 후 목록, 0개면 서버를 모델에 붙이지 않음
                servers, amp = [server], "있음"
            else:
                amp = amplitude.MISMATCH
                await server.cleanup()
        except Exception as e:  # Amplitude가 막혀도 나머지 소스로 답변
            log.warning("amplitude unavailable: %s", e)
            amp = "없음(연결 실패)"
    try:
        agent = Agent(name="kbap-pm-agent", instructions=f"{system}, Amplitude {amp}", model=_model(model),
                      tools=ftools, mcp_servers=servers, output_type=AgentAnswer)
        result = Runner.run_streamed(agent, input=history, max_turns=max_turns())  # 모델 호출 1회 = 1턴
        mcp_calls: dict[str, tuple] = {}  # call_id → 원문 조회 키
        try:
            async for ev in result.stream_events():
                if ev.type != "run_item_stream_event":
                    continue
                raw = ev.item.raw_item
                if ev.name == "tool_called" and getattr(raw, "name", None) not in fnames:  # MCP 도구는 SDK 이벤트로 알림
                    mcp_calls[_call_id(raw)] = amplitude.call_key(raw.name, json.loads(raw.arguments or "{}"))
                    await emit({"type": "tool_call", "key": _call_id(raw), "source": "amplitude", "name": raw.name,
                                "input": json.loads(raw.arguments or "{}")})
                elif ev.name == "tool_output" and _call_id(raw) in mcp_calls:
                    out = _text(ev.item.output)
                    stash = type(server).originals.get(mcp_calls[_call_id(raw)]) if server else None
                    if stash:  # 모델에는 잘린 사본, 이벤트·DB에는 원문
                        out = stash.pop(0)
                    failed = out.startswith(FAIL) or bool((getattr(ev.item, "custom_data", None) or {}).get("is_error"))
                    await emit({"type": "tool_result", "key": _call_id(raw), "status": "failed" if failed else "succeeded",
                                "summary": out.splitlines()[0][:500] if out else "", "text": out})
        except MaxTurnsExceeded:  # max_turns 다음 모델 호출 직전 정지(마지막 턴의 도구는 실행됨)
            raise TurnLimit()
        finally:
            # ponytail: 실행 전체 합계를 한 번 기록(요청별 행 아님). 요청별 비용이 필요하면 raw_responses 순회로
            u = result.context_wrapper.usage
            usage(u.input_tokens, u.output_tokens)
        return result.final_output.model_dump_json(by_alias=True)
    finally:
        if servers:
            await server.cleanup()


async def summarize(model: str, prompt: str) -> tuple[str, int, int]:
    result = await Runner.run(Agent(name="code-summary", model=_model(model)), prompt)
    u = result.context_wrapper.usage
    return str(result.final_output), u.input_tokens, u.output_tokens


async def refine(model: str, prompt: str):
    """질문 다듬기: 도구 없는 단발 실행, 구조화 출력 RefineResult"""
    from app.schemas import RefineResult
    result = await Runner.run(Agent(name="question-refine", model=_model(model), output_type=RefineResult), prompt)
    u = result.context_wrapper.usage
    return result.final_output, u.input_tokens, u.output_tokens
