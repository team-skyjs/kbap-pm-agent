"""Anthropic 공식 SDK 런타임. 상한·이벤트·사용량 기록·사후 검증은 agent.py, 여기는 SDK 호출만."""
import contextlib
import logging

from anthropic import AsyncAnthropic, beta_async_tool

from app import amplitude
from app.config import is_fake

log = logging.getLogger("app.agent_anthropic")
BETAS = ["server-side-fallback-2026-07-01"]  # fallbacks="default"와 짝 (배열형은 2026-06-01 헤더라 섞으면 400)


def _client() -> AsyncAnthropic:
    """검사 스크립트가 가짜 전송(httpx2.MockTransport)을 넣은 클라이언트로 교체."""
    return AsyncAnthropic()


def _mcp_call(name: str, session):
    async def call(**kwargs) -> str:
        result = await session.call_tool(name, kwargs)
        text = "\n".join(getattr(c, "text", "") for c in result.content)
        if result.isError:
            raise RuntimeError(text[:300] or "MCP 도구 오류")
        return text
    return call


def _usage(u) -> tuple[int, int]:
    # ponytail: 캐시 쓰기·읽기 토큰도 입력 단가로 계산(쓰기 1.25배는 과소, 읽기 0.1배는 과대, 대체로 보수적). 정확히 하려면 단가표에 캐시 단가 추가
    cached = (u.cache_creation_input_tokens or 0) + (u.cache_read_input_tokens or 0)
    return u.input_tokens + cached, u.output_tokens


async def run(model: str, system: str, history: list[dict], tools: list, emit, usage) -> str:
    """도구 루프 실행 후 최종 AgentAnswer JSON 문자열 반환. 거절이면 agent.Refused."""
    from app.agent import Refused, TurnLimit, max_turns, wrap
    from app.schemas import AgentAnswer

    btools = [beta_async_tool(t) for t in tools]
    amp = "없음(연결 안 됨)"
    async with contextlib.AsyncExitStack() as stack:  # MCP 세션은 이 태스크 안에서 열고 닫기(anyio 취소 범위)
        try:
            mcp = await stack.enter_async_context(amplitude.anthropic_tools())
        except Exception as e:  # Amplitude가 막혀도 나머지 소스로 답변
            log.warning("amplitude unavailable: %s", e)
            mcp, amp = [], "없음(연결 실패)"
        for t, session in mcp:
            btools.append(beta_async_tool(wrap(_mcp_call(t.name, session), emit, "amplitude", name=t.name),
                                          name=t.name, description=t.description or t.name, input_schema=t.inputSchema))
        if mcp:
            amp = "있음"
        elif amp == "없음(연결 안 됨)" and amplitude.connected() and not is_fake():  # 연결은 됐지만 허용 목록과 0개 일치
            amp = amplitude.MISMATCH
        runner = _client().beta.messages.tool_runner(
            model=model, max_tokens=16000, system=f"{system}, Amplitude {amp}", messages=history, tools=btools,
            output_format=AgentAnswer, thinking={"type": "adaptive"}, cache_control={"type": "ephemeral"},
            betas=BETAS, fallbacks="default", max_iterations=max_turns())  # 반복 1회 = 모델 요청 1회 = 1턴
        last = None
        async for message in runner:  # tool_choice 미지정(auto). 현행 모델은 any/tool 강제를 400으로 거부
            usage(*_usage(message.usage))
            if message.stop_reason == "refusal":  # 본문을 읽기 전에 확인
                raise Refused()
            last = message
        if last is None:
            raise RuntimeError("모델 응답이 없습니다.")
        if last.stop_reason == "tool_use":  # max_iterations 도달로 도구 결과만 받고 종료(마지막 턴의 도구는 실행됨)
            raise TurnLimit()
        return next(b.text for b in last.content if b.type == "text")


async def summarize(model: str, prompt: str) -> tuple[str, int, int]:
    resp = await _client().messages.create(model=model, max_tokens=4000, output_config={"effort": "low"},
                                           messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in resp.content if b.type == "text"), *_usage(resp.usage)


# 질문 다듬기에서 사고를 끄는 모델. 한 문장 재작성이라 사고가 지연만 늘림.
# ponytail: disabled를 받는 것이 확인된 모델만(Haiku 5.5는 effort high 이하에서 허용, Sonnet·Opus 5.5·Fable은 400)
REFINE_THINKING_OFF = {"claude-haiku-5-5"}


async def refine(model: str, prompt: str):
    """질문 다듬기: 도구·tool_choice 없이 구조화 출력 1회. 거절이면 agent.Refused"""
    from app.agent import Refused
    from app.schemas import RefineResult
    extra = {"thinking": {"type": "disabled"}} if model in REFINE_THINKING_OFF else {}
    resp = await _client().messages.parse(model=model, max_tokens=2000, output_format=RefineResult,
                                          output_config={"effort": "low"},
                                          messages=[{"role": "user", "content": prompt}], **extra)
    if resp.stop_reason == "refusal":  # 본문을 읽기 전에 확인
        raise Refused()
    if resp.parsed_output is None:
        raise ValueError("구조화 출력 없음")
    return resp.parsed_output, *_usage(resp.usage)
