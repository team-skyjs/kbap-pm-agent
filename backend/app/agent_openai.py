"""OpenAI Agents SDK 런타임 (ADR-20). agent.py가 상한·이벤트·사용량 기록·사후 검증을 맡고, 여기는 SDK 호출만 한다."""
import json
import logging

from agents import Agent, OpenAIResponsesModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from app import amplitude
from app.config import num

log = logging.getLogger("app.agent_openai")
# ponytail: SDK 기본 트레이싱은 실행 내용을 OpenAI 트레이스 대시보드로 내보낸다. 요청받지 않은 외부 전송이라 끈다. 필요하면 env로 켜기
set_tracing_disabled(True)
FAIL = "도구 오류:"  # MCP 실패 결과 머리말. 이걸로 tool_result failed를 판별한다


def _client() -> AsyncOpenAI:
    """검사 스크립트가 httpx.MockTransport를 넣은 클라이언트로 바꿔 끼운다."""
    return AsyncOpenAI()


def _model(name: str) -> OpenAIResponsesModel:
    return OpenAIResponsesModel(model=name, openai_client=_client())


def _mcp_failure(_ctx, error: Exception) -> str:
    return f"{FAIL} {type(error).__name__}: {str(error)[:300]}"


def _mcp_error_flag(ctx) -> dict:
    return {"is_error": bool(ctx.is_error)}  # MCP isError 결과는 예외가 아니라 일반 출력으로 와서 따로 실어 나른다


def _text(output) -> str:
    """MCP 출력은 내용 블록(dict 또는 목록)으로 온다. 사람이 읽을 텍스트만 뽑는다."""
    blocks = output if isinstance(output, list) else [output]
    return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in blocks)


def _call_id(raw) -> str | None:
    return raw.get("call_id") if isinstance(raw, dict) else getattr(raw, "call_id", None)


async def run(model: str, system: str, history: list[dict], tools: list, emit, usage) -> str:
    """도구 루프를 돌려 최종 AgentAnswer JSON 문자열을 돌려준다."""
    from app.schemas import AgentAnswer

    ftools = [function_tool(t) for t in tools]  # 이벤트는 공통 래퍼가 낸다
    fnames = {t.name for t in ftools}
    server, servers, amp = amplitude.openai_server(failure_error_function=_mcp_failure,
                                                                custom_data_extractor=_mcp_error_flag), [], "없음(연결 안 됨)"
    if server:
        try:
            await server.connect()
            servers, amp = [server], "있음"
        except Exception as e:  # Amplitude가 막혀도 나머지 소스로 답한다(US1-4)
            log.warning("amplitude unavailable: %s", e)
            amp = "없음(연결 실패)"
    try:
        agent = Agent(name="kbap-pm-agent", instructions=f"{system}, Amplitude {amp}", model=_model(model),
                      tools=ftools, mcp_servers=servers, output_type=AgentAnswer)
        result = Runner.run_streamed(agent, input=history, max_turns=int(num("AGENT_MAX_TOOL_CALLS", 20)) + 2)
        mcp_calls: set[str] = set()
        try:
            async for ev in result.stream_events():
                if ev.type != "run_item_stream_event":
                    continue
                raw = ev.item.raw_item
                if ev.name == "tool_called" and getattr(raw, "name", None) not in fnames:  # MCP 도구 → SDK 이벤트로 알린다
                    mcp_calls.add(_call_id(raw))
                    await emit({"type": "tool_call", "key": _call_id(raw), "source": "amplitude", "name": raw.name,
                                "input": json.loads(raw.arguments or "{}")})
                elif ev.name == "tool_output" and _call_id(raw) in mcp_calls:
                    out = _text(ev.item.output)
                    failed = out.startswith(FAIL) or bool((getattr(ev.item, "custom_data", None) or {}).get("is_error"))
                    await emit({"type": "tool_result", "key": _call_id(raw), "status": "failed" if failed else "succeeded",
                                "summary": out.splitlines()[0][:500] if out else "", "text": out})
        finally:
            # ponytail: 실행 전체 합계를 한 번 기록한다(요청별 행 아님). 요청별 비용이 필요하면 raw_responses 순회로
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
