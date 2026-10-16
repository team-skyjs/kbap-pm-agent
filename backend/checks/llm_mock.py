"""두 LLM SDK에 가짜 HTTP 전송을 넣는 검사 도우미. 실제 SDK 요청 생성·응답 파싱 경로를 그대로 사용. 비용 0.
스크립트 단계: ("tool", 도구이름, 입력) | ("tools", [(도구이름, 입력), ...]) 병렬 호출 | ("final", AgentAnswer dict)
| ("raw", 텍스트) 그대로의 텍스트 응답(잘못된 JSON 시험) | ("refusal",) | ("http400",) 요청 거부"""
import asyncio
import json

import httpx
import httpx2
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app import agent_anthropic, agent_openai

sent: list = []  # 보낸 요청 본문 (검사에서 확인용)


def _calls(step):
    return [(step[1], step[2])] if step[0] == "tool" else step[1]


def _anthropic_reply(step, n):
    usage = {"input_tokens": 100, "output_tokens": 10}
    if step[0] in ("tool", "tools"):
        content = [{"type": "tool_use", "id": f"tu{n}_{i}", "name": name, "input": args}
                   for i, (name, args) in enumerate(_calls(step))]
        stop = "tool_use"
    elif step[0] in ("final", "raw"):
        text = step[1] if step[0] == "raw" else json.dumps(step[1], ensure_ascii=False)
        content, stop = [{"type": "text", "text": text}], "end_turn"
    else:
        content, stop = [], "refusal"
    return {"id": f"msg{n}", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None, "usage": usage}


def _openai_reply(step, n, stream=True):
    if step[0] in ("tool", "tools"):
        out = [{"type": "function_call", "id": f"fc{n}_{i}", "call_id": f"call{n}_{i}", "name": name,
                "arguments": json.dumps(args), "status": "completed"} for i, (name, args) in enumerate(_calls(step))]
    else:
        out = [{"type": "message", "id": f"m{n}", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "annotations": [],
                             "text": step[1] if step[0] == "raw" else json.dumps(step[1], ensure_ascii=False)}]}]
    r = {"id": f"r{n}", "object": "response", "created_at": 1, "model": "gpt-6-luna", "status": "completed", "output": out,
         "parallel_tool_calls": True, "tool_choice": "auto", "tools": [],
         "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110,
                   "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}
    if not stream:  # Runner.run(비스트리밍)은 응답 객체 JSON을 받음
        return r
    return "".join(f"event: {t}\ndata: {json.dumps({'type': t, 'sequence_number': k, 'response': r})}\n\n"
                   for k, t in enumerate(["response.created", "response.completed"]))


def script(provider: str, steps, delay: float = 0.0):
    """steps는 리스트 또는 무한 이터레이터. delay초마다 응답(시간 상한 시험용)."""
    it = iter(steps)
    sent.clear()

    async def handler(req):
        sent.append(json.loads(req.content))
        if delay:
            await asyncio.sleep(delay)
        step, n = next(it), len(sent)
        if step[0] == "http400":
            err = {"type": "error", "error": {"type": "invalid_request_error", "message": "rejected"}}
            return (httpx2 if provider == "anthropic" else httpx).Response(400, json=err)
        if provider == "anthropic":
            return httpx2.Response(200, json=_anthropic_reply(step, n))
        if not sent[-1].get("stream"):
            return httpx.Response(200, json=_openai_reply(step, n, stream=False))
        return httpx.Response(200, text=_openai_reply(step, n), headers={"content-type": "text/event-stream"})

    if provider == "anthropic":  # anthropic 1.x SDK는 httpx2 사용
        agent_anthropic._client = lambda: AsyncAnthropic(api_key="test", max_retries=0, http_client=httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler)))
    else:
        agent_openai._client = lambda: AsyncOpenAI(api_key="test", max_retries=0, http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler)))


def sse(c, cid: int, content: str = "질문", skip_amplitude: bool = True) -> list[tuple[str, dict]]:
    """메시지 전송 SSE 이벤트 목록. 기본은 Amplitude 사전 점검을 건너뜀(점검·도구는 check_b12 몫)"""
    body = {"content": content, "skipAmplitude": True} if skip_amplitude else {"content": content}
    with c.stream("POST", f"/api/conversations/{cid}/messages", json=body) as r:
        assert r.status_code == 200, r.read()
        evs, ev = [], None
        for line in r.iter_lines():
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                evs.append((ev, json.loads(line[6:])))
    return evs
