"""OpenAI Agents SDK 런타임. 상한·이벤트·사용량 기록·사후 검증은 agent.py, 여기는 SDK 호출만."""
import logging

from agents import Agent, MaxTurnsExceeded, OpenAIResponsesModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from app.errors import ToolError

log = logging.getLogger("app.agent_openai")
# ponytail: SDK 기본 트레이싱이 실행 내용(코드 발췌·지표)을 OpenAI 트레이스로 전송. 외부 유출 방지를 위해 비활성
set_tracing_disabled(True)


def _client() -> AsyncOpenAI:
    """검사 스크립트가 가짜 전송(httpx.MockTransport)을 넣은 클라이언트로 교체."""
    return AsyncOpenAI()


def _model(name: str) -> OpenAIResponsesModel:
    return OpenAIResponsesModel(model=name, openai_client=_client())


def _failure(_ctx, error: Exception) -> str:
    """SDK 기본값은 고정 문장이라 모델이 인자 오류를 고칠 수 없음. 공통 래퍼와 같은 실패 문장 전달"""
    return str(error)[:500] if isinstance(error, ToolError) else f"도구 오류: {type(error).__name__}: {str(error)[:300]}"


async def run(model: str, system: str, history: list[dict], tools: list, emit, usage) -> str:
    """도구 루프 실행 후 최종 AgentAnswer JSON 문자열 반환. 도구 이벤트는 공통 래퍼 담당."""
    from app.agent import TurnLimit, max_turns
    from app.schemas import AgentAnswer

    agent = Agent(name="kbap-pm-agent", instructions=system, model=_model(model),
                  tools=[function_tool(t, failure_error_function=_failure) for t in tools], output_type=AgentAnswer)
    result = Runner.run_streamed(agent, input=history, max_turns=max_turns())  # 모델 호출 1회 = 1턴
    try:
        async for _ in result.stream_events():
            pass
    except MaxTurnsExceeded:  # max_turns 다음 모델 호출 직전 정지(마지막 턴의 도구는 실행됨)
        raise TurnLimit()
    finally:
        # ponytail: 실행 전체 합계를 한 번 기록(요청별 행 아님). 요청별 비용이 필요하면 raw_responses 순회로
        u = result.context_wrapper.usage
        usage(u.input_tokens, u.output_tokens)
    return result.final_output.model_dump_json(by_alias=True)


async def summarize(model: str, prompt: str) -> tuple[str, int, int]:
    result = await Runner.run(Agent(name="code-summary", model=_model(model)), prompt)
    u = result.context_wrapper.usage
    return str(result.final_output), u.input_tokens, u.output_tokens


async def refine(model: str, prompt: str):
    """질문 다듬기: 도구 없는 단발 실행, 구조화 출력 RefineResult. 거절·형식 오류는 usage를 실은 agent.Malformed"""
    from agents import RunHooks
    from agents.exceptions import AgentsException

    from app.agent import Malformed
    from app.schemas import RefineResult

    class Tokens(RunHooks):  # 모델 응답마다 사용량 누적: 출력 검증이 실패해도 쓴 토큰을 기록하기 위해
        input = output = 0

        async def on_llm_end(self, context, agent, response):
            self.input += response.usage.input_tokens
            self.output += response.usage.output_tokens
    tokens = Tokens()
    try:
        result = await Runner.run(Agent(name="question-refine", model=_model(model), output_type=RefineResult), prompt,
                                  hooks=tokens)
    except AgentsException as e:  # 거절·잘못된 출력
        raise Malformed((tokens.input, tokens.output) if tokens.input or tokens.output else None, type(e).__name__) from e
    return result.final_output, tokens.input, tokens.output
