"""B6 검사: AgentAnswer 규칙, 그리고 실제 에이전트 루프(create_agent)를 가짜 채팅 모델로 돌려
도구 이벤트·구조화 final·도구 실패 계속·상한 부분 final·모델 실패 error를 확인한다. 실제 LLM 호출 없음."""
import copy
import itertools
import json
import os

from common import client, ok
from examples import CONV_DETAIL, PROPOSAL_15, TAXONOMY_BODY
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app import agent, code_tools
from app.schemas import AgentAnswer, Message

draft = lambda p: {k: v for k, v in p.items() if k not in ("id", "conversationId", "messageId", "seq", "decision", "createdAt")}  # noqa: E731
imp = draft(CONV_DETAIL["messages"][1]["proposals"][0])
fun = draft(PROPOSAL_15)
AgentAnswer.model_validate({"content": "x", "proposals": [imp, fun]})


def rejects(mut):
    p = copy.deepcopy(fun)
    mut(p)
    try:
        AgentAnswer.model_validate({"content": "x", "proposals": [p]})
    except ValidationError:
        return True
    return False


assert rejects(lambda p: p["measurement"]["funnel"][1].update(location=None))
assert rejects(lambda p: p["measurement"]["funnel"][2].update(order=4))
assert rejects(lambda p: p["measurement"].update(funnel=[]))
assert rejects(lambda p: p["measurement"]["funnel"][0].update(location={"file": "a", "function": "b", "line": 1}))
assert rejects(lambda p: p.update(evidence=[]))
assert rejects(lambda p: p["evidence"][1].update(value="x"))  # 다른 kind 필드
ok("AgentAnswer: 계약 예시 통과, new location null·order 불연속·빈 funnel·잘못된 kind 필드 거부")


class Scripted(GenericFakeChatModel):
    def bind_tools(self, tools, **kw):
        return self


def ai(tool, args, i):
    return AIMessage(content="", tool_calls=[{"name": tool, "args": args, "id": f"c{i}"}],
                     usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})


def run(c, script):
    agent._model = lambda: Scripted(messages=iter(script))
    cid = c.post("/api/conversations", json={}).json()["id"]
    with c.stream("POST", f"/api/conversations/{cid}/messages", json={"content": "장바구니 측정 설계"}) as r:
        assert r.status_code == 200, r.read()
        evs, ev = [], None
        for line in r.iter_lines():
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                evs.append((ev, json.loads(line[6:])))
    return cid, evs


c = client()
c.put("/api/settings/taxonomy", json=TAXONOMY_BODY)
os.environ["AGENT_MODE"] = "real"
os.environ["AGENT_MODEL"] = "anthropic:claude-sonnet-5-5"
try:
    answer = {"content": "장바구니 퍼널을 설계했습니다.", "proposals": [fun]}
    cid, evs = run(c, [ai("search_taxonomy", {"query": "scan"}, 1), AIMessage(content=json.dumps(answer, ensure_ascii=False), usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})])
    assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], [e for e, _ in evs]
    assert evs[1][1]["source"] == "taxonomy" and evs[2][1]["status"] == "succeeded"
    assert evs[2][1]["resultSummary"].startswith("일치 이벤트 2개")
    final = Message.model_validate(evs[-1][1])
    assert final.status == "completed" and final.proposals[0].type == "funnel_design"
    assert final.usage.input_tokens == 200 and final.usage.cost_usd > 0
    assert c.get(f"/api/conversations/{cid}").json()["messages"][1] == evs[-1][1]
    ok("real 루프: 도구 호출 → 구조화 final, usage 기록, GET 상세 일치")

    def boom(query: str) -> str:
        """택사노미 검색."""
        raise RuntimeError("Amplitude 연결 끊김")
    real = code_tools.TAXONOMY_TOOLS
    boom.__name__ = "search_taxonomy"
    code_tools.TAXONOMY_TOOLS = [boom, real[1]]
    cid, evs = run(c, [ai("search_taxonomy", {"query": "x"}, 1), AIMessage(content=json.dumps({"content": "택사노미 근거가 빠졌습니다.", "proposals": []}, ensure_ascii=False))])
    code_tools.TAXONOMY_TOOLS = real
    assert evs[2][1]["status"] == "failed" and evs[-1][0] == "final", evs
    ok("도구 예외 → tool_result failed, 실행은 final로 계속")

    os.environ["AGENT_MAX_TOOL_CALLS"] = "2"
    cid, evs = run(c, (ai("search_taxonomy", {"query": "scan"}, i) for i in itertools.count()))
    os.environ.pop("AGENT_MAX_TOOL_CALLS")
    assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "tool_call", "tool_result", "final"]
    final = Message.model_validate(evs[-1][1])
    assert final.status == "completed" and final.proposals == []
    assert final.content.startswith("도구 호출 상한(2회)에 도달해 여기까지의 조회 결과로 답합니다."), final.content
    ok("도구 호출 상한 → 부분 final(completed, 사유 첫 문장, proposals [])")

    class Slow(Scripted):
        async def _agenerate(self, *a, **kw):
            import asyncio
            await asyncio.sleep(0.6)
            return await super()._agenerate(*a, **kw)
    os.environ["AGENT_TIMEOUT_SECONDS"] = "1"
    agent_model_backup = agent._model
    agent._model = lambda: Slow(messages=(ai("search_taxonomy", {"query": "scan"}, i) for i in itertools.count()))
    cid = c.post("/api/conversations", json={}).json()["id"]
    with c.stream("POST", f"/api/conversations/{cid}/messages", json={"content": "느린 실행"}) as r:
        last = [l for l in r.iter_lines() if l.startswith("data: ")][-1]
    os.environ.pop("AGENT_TIMEOUT_SECONDS")
    final = Message.model_validate(json.loads(last[6:]))
    assert final.status == "completed" and final.content.startswith("실행 시간 상한(1초)에 도달해"), final.content
    assert all(t.status != "running" for t in final.tool_calls)
    ok("실행 시간 상한 → 부분 final, running 도구 호출 없음")

    class Broken(Scripted):
        async def _agenerate(self, *a, **kw):
            raise ConnectionError("provider down")
    agent._model = lambda: Broken(messages=iter([]))
    cid = c.post("/api/conversations", json={}).json()["id"]
    with c.stream("POST", f"/api/conversations/{cid}/messages", json={"content": "실패"}) as r:
        lines = list(r.iter_lines())
    assert "event: error" in lines
    err = json.loads(lines[lines.index("event: error") + 1][6:])
    assert err["error"]["code"] == "UPSTREAM_ERROR" and set(err) == {"error", "assistantMessageId"}
    m = c.get(f"/api/conversations/{cid}").json()["messages"][1]
    assert m["status"] == "failed" and m["errorCode"] == "UPSTREAM_ERROR"
    ok("모델 호출 실패 → error UPSTREAM_ERROR, 메시지 failed")
finally:
    os.environ["AGENT_MODE"] = "fake"
print("check_b6 OK")
