"""B9 검사(ADR-20): AgentAnswer 규칙, 그리고 두 런타임(anthropic tool runner, openai-agents)에 가짜 HTTP 전송을 넣어
실제 SDK 경로로 SSE 순서·사용량·도구 실패·사후 검증·거절·시간/호출 상한·접두사 검사를 확인한다. 실제 LLM 호출 없음."""
import copy
import itertools
import json
import os
import pathlib
import tempfile

from common import client, ok
from examples import CONV_DETAIL, PROPOSAL_15, TAXONOMY_BODY
from llm_mock import script, sent, sse
from pydantic import ValidationError

from app import agent, code_tools, db, repo
from app.schemas import AgentAnswer, Message

draft = lambda p: {k: v for k, v in p.items() if k not in ("id", "conversationId", "messageId", "seq", "decision", "createdAt")}  # noqa: E731
imp, fun = draft(CONV_DETAIL["messages"][1]["proposals"][0]), draft(PROPOSAL_15)
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
assert rejects(lambda p: p["evidence"][1].update(value="x"))
ok("AgentAnswer: 계약 예시 통과, 교차 규칙 위반 거부")

# 등록된 저장소처럼 보이게: 인덱스 파일만 두면 find_event_calls가 돈다(rg 불필요)
os.environ["REPOS_DIR"] = tmp = tempfile.mkdtemp()
(pathlib.Path(tmp) / "repo").mkdir()
(pathlib.Path(tmp) / "index.json").write_text(json.dumps({"scan_complete": [{"file": "src/app/scan.tsx", "line": 405, "function": "fail"}]}))
c = client()
repo.update(url="file:///x", branch="main", headCommit="abc1234")
c.put("/api/settings/taxonomy", json=TAXONOMY_BODY)
answer = {"content": "스캔 퍼널을 분석했습니다.", "proposals": [imp, fun]}
bad_location = copy.deepcopy(answer)
bad_location["proposals"][1]["measurement"]["funnel"][1]["location"] = None


def usage_rows(mid):
    return db.one("SELECT COUNT(*) AS n FROM llm_usage WHERE message_id = %s", (mid,))["n"]


def new_conv():
    return c.post("/api/conversations", json={}).json()["id"]


os.environ["AGENT_MODE"] = "real"
try:
    for provider, model in [("anthropic", "anthropic:claude-sonnet-5-5"), ("openai", "openai:gpt-6-luna")]:
        os.environ["AGENT_MODEL"] = model
        script(provider, [("tool", "find_event_calls", {"eventName": "scan_complete"}), ("final", answer)])
        evs = sse(c, new_conv())
        assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], [e for e, _ in evs]
        assert evs[1][1]["source"] == "code" and evs[1][1]["input"] == {"eventName": "scan_complete"}
        assert evs[2][1]["status"] == "succeeded" and evs[2][1]["resultSummary"] == "1곳: src/app/scan.tsx:405 (fail)"
        final = Message.model_validate(evs[-1][1])
        assert final.status == "completed" and [p.type for p in final.proposals] == ["improvement", "funnel_design"]
        assert usage_rows(final.id) >= 1 and final.usage.input_tokens > 0 and final.usage.cost_usd > 0
        assert c.get(f"/api/conversations/{evs[0][1]['userMessage']['conversationId']}").json()["messages"][1] == evs[-1][1]
        if provider == "anthropic":
            req = sent[0]
            assert "tool_choice" not in req and req["thinking"] == {"type": "adaptive"} and req["fallbacks"] == "default"
            assert req["cache_control"] == {"type": "ephemeral"} and req["output_config"]["format"]["type"] == "json_schema"
            assert {t["name"] for t in req["tools"]} >= {"find_event_calls", "read_code", "search_taxonomy"}
        else:
            assert sent[0]["text"]["format"]["type"] == "json_schema"
            assert {t["name"] for t in sent[0]["tools"]} >= {"find_event_calls", "read_code", "search_taxonomy"}
        ok(f"{provider}: 도구 호출 → 구조화 final, SSE 순서, llm_usage 기록, GET 상세 일치, 요청 파라미터")

        def boom(eventName: str) -> str:
            """이벤트 호출 위치를 찾는다.

            Args:
                eventName: 이벤트 이름
            """
            raise RuntimeError("인덱스 파일 손상")
        real = code_tools.CODE_TOOLS
        boom.__name__ = "find_event_calls"
        code_tools.CODE_TOOLS = [boom, *real[1:]]
        script(provider, [("tool", "find_event_calls", {"eventName": "x"}), ("final", {"content": "코드 근거가 빠졌습니다.", "proposals": []})])
        evs = sse(c, new_conv())
        code_tools.CODE_TOOLS = real
        assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], evs
        assert evs[2][1]["status"] == "failed" and evs[2][1]["resultSummary"].startswith("도구 오류: RuntimeError")
        ok(f"{provider}: 도구 예외 → tool_result failed, 실행은 final로 계속")

        script(provider, [("final", bad_location)])
        evs = sse(c, new_conv())
        assert evs[-1][0] == "error" and evs[-1][1]["error"]["code"] == "UPSTREAM_ERROR", evs[-1]
        m = c.get(f"/api/conversations/{evs[0][1]['userMessage']['conversationId']}").json()["messages"][1]
        assert m["status"] == "failed" and m["errorCode"] == "UPSTREAM_ERROR"
        ok(f"{provider}: 신규 단계 location null → error UPSTREAM_ERROR, 메시지 failed")

        # 턴 상한: 모델 요청 1회 = 1턴, 병렬 도구 호출 응답도 1턴. AGENT_MAX_TURNS=2면 두 번째 모델 응답의 도구까지 실행 후 멈춘다
        os.environ["AGENT_MAX_TURNS"] = "2"
        script(provider, itertools.chain(
            [("tools", [("search_taxonomy", {"query": "scan"}), ("get_event_definition", {"name": "scan_start"})])],
            (("tool", "search_taxonomy", {"query": "scan"}) for _ in itertools.count())))
        evs = sse(c, new_conv())
        os.environ.pop("AGENT_MAX_TURNS")
        assert len(sent) == 2, f"모델 요청 {len(sent)}회 (2회여야 함)"
        assert [e for e, _ in evs].count("tool_call") == 3 and [e for e, _ in evs].count("tool_result") == 3, [e for e, _ in evs]
        assert evs[-1][0] == "final", evs[-1]
        final = Message.model_validate(evs[-1][1])
        assert final.status == "completed" and final.proposals == []
        assert final.content.startswith("모델 호출 상한(2턴)에 도달해 여기까지의 조회 결과로 답합니다."), final.content
        assert all(t.status == "succeeded" for t in final.tool_calls)
        ok(f"{provider}: AGENT_MAX_TURNS=2 → 모델 요청 2회(병렬 2개 = 1턴), 도구 3회 실행 후 부분 final")

        os.environ["AGENT_TIMEOUT_SECONDS"] = "1"
        script(provider, (("tool", "search_taxonomy", {"query": "scan"}) for _ in itertools.count()), delay=0.6)
        evs = sse(c, new_conv())
        os.environ.pop("AGENT_TIMEOUT_SECONDS")
        final = Message.model_validate(evs[-1][1])
        assert evs[-1][0] == "final" and final.content.startswith("실행 시간 상한(1초)에 도달해"), final.content
        assert all(t.status != "running" for t in final.tool_calls)
        ok(f"{provider}: AGENT_TIMEOUT_SECONDS=1 + 지연 전송 → 부분 final, running 도구 호출 없음")

    os.environ["AGENT_MODEL"] = "anthropic:claude-sonnet-5-5"
    script("anthropic", [("refusal",)])
    evs = sse(c, new_conv())
    assert evs[-1][0] == "error" and evs[-1][1]["error"]["code"] == "UPSTREAM_ERROR" and "거절" in evs[-1][1]["error"]["message"]
    ok("anthropic: stop_reason refusal → error UPSTREAM_ERROR")

    os.environ["AGENT_MODEL"] = "foo:bar"
    try:
        agent.check_models()
        raise AssertionError("모르는 접두사가 통과함")
    except ValueError:
        pass
    from fastapi.testclient import TestClient

    from app.main import app
    try:
        with TestClient(app):
            raise AssertionError("모르는 접두사로 서버가 떴다")
    except ValueError:
        pass
    ok("알 수 없는 접두사 foo:bar → 기동 실패")
finally:
    os.environ["AGENT_MODE"] = "fake"
    os.environ["AGENT_MODEL"] = "anthropic:claude-sonnet-5-5"

root = pathlib.Path(__file__).resolve().parent.parent
hits = [str(p) for p in [*(root / "app").rglob("*.py"), root / "pyproject.toml"] if "langchain" in p.read_text()]
assert hits == [], hits
ok("backend/app, pyproject.toml에 langchain 없음")
print("check_b6 OK")
