"""Amplitude 검사: fake connect = 계약 예시 URL + 즉시 connected, 콜백 text/html, Amplitude 도구 예외·연결 실패에도 실행은 final로 종료.
실제 OAuth 승인은 브라우저가 필요해 제외."""
import json
import os

from common import client, ok
from examples import AUTH_URL
from app import amplitude
from app.schemas import Message

c = client()
s = c.get("/api/settings").json()["amplitude"]
assert s == {"status": "disconnected", "serverUrl": "https://mcp.amplitude.com/mcp", "connectedAt": None}, s
r = c.post("/api/integrations/amplitude/connect")
assert r.status_code == 200 and r.json() == {"authorizationUrl": AUTH_URL}, r.text
s = c.get("/api/settings").json()["amplitude"]
assert s["status"] == "connected" and s["connectedAt"].endswith("Z")
ok("fake connect = 계약 예시 URL, 직후 amplitude.status connected")

r = c.get("/api/integrations/amplitude/callback", params={"code": "x", "state": "y"})
assert r.status_code == 200 and r.headers["content-type"].startswith("text/html") and "Amplitude 연결 실패" in r.text
r = c.get("/api/integrations/amplitude/callback", params={"error": "access_denied"})
assert "Amplitude 연결 실패: access_denied" in r.text
os.environ["ACCESS_TOKEN"] = "t"
assert c.get("/api/integrations/amplitude/callback").status_code == 200  # 인증 불필요
os.environ["ACCESS_TOKEN"] = ""
ok("콜백 text/html, 인증 없이 접근, 실패 문구")


# --- 실제 MCP 프로토콜로 도는 로컬 가짜 Amplitude 서버(FastMCP, 인증 없음이라 OAuth provider는 통과만)
import threading  # noqa: E402
import time  # noqa: E402

import uvicorn  # noqa: E402
from llm_mock import script, sse  # noqa: E402
from mcp.client.auth import OAuthClientProvider  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

fake_amp = FastMCP("amplitude", stateless_http=True)


@fake_amp.tool()
def query_funnel(events: list[str]) -> str:
    """Amplitude 퍼널 조회."""
    if events == ["boom"]:
        raise RuntimeError("Amplitude MCP 차단")
    return "scan_start 2,418명 → scan_complete 999명, 전환율 41.3%"


server = uvicorn.Server(uvicorn.Config(fake_amp.streamable_http_app(), host="127.0.0.1", port=8766, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.05)
os.environ["AMPLITUDE_MCP_URL"] = "http://127.0.0.1:8766/mcp"
done = {"content": "Amplitude 지표 근거가 빠졌습니다. 코드·택사노미만으로 답합니다.", "proposals": []}
os.environ["AGENT_MODE"] = "real"
try:
    assert amplitude.connected()  # 위 fake connect가 남긴 상태

    async def names():
        async with amplitude.anthropic_tools() as tools:
            return [t.name for t, _ in tools]
    import asyncio  # noqa: E402
    assert asyncio.run(names()) == ["query_funnel"]
    srv = amplitude.openai_server()
    assert isinstance(srv.params["auth"], OAuthClientProvider) and srv.params["url"] == os.environ["AMPLITUDE_MCP_URL"]
    ok("anthropic_tools()가 MCP 도구를 내고, openai_server()가 같은 OAuth provider를 params['auth']로 넘긴다")

    for provider, model in [("anthropic", "anthropic:claude-sonnet-5-5"), ("openai", "openai:gpt-6-luna")]:
        os.environ["AGENT_MODEL"] = model
        cid = c.post("/api/conversations", json={}).json()["id"]
        script(provider, [("tool", "query_funnel", {"events": ["scan_start"]}), ("final", done)])
        evs = sse(c, cid)
        assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], evs
        assert evs[1][1]["source"] == "amplitude" and evs[2][1]["status"] == "succeeded"
        assert "41.3%" in evs[2][1]["resultSummary"]
        cid = c.post("/api/conversations", json={}).json()["id"]
        script(provider, [("tool", "query_funnel", {"events": ["boom"]}), ("final", done)])
        evs = sse(c, cid)
        assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], evs
        assert evs[1][1]["source"] == "amplitude" and evs[2][1]["status"] == "failed", evs[2]
        assert "Amplitude MCP 차단" in evs[2][1]["resultSummary"] and not evs[2][1]["resultSummary"].startswith("{"), evs[2]
        Message.model_validate(evs[-1][1])
        ok(f"{provider}: MCP 도구 성공(source amplitude), MCP isError → tool_result failed 후 final")

        # 클라이언트 예외 경로(Amplitude 다운·연결 끊김): call_tool 자체가 ConnectionError 발생
        from mcp import ClientSession  # noqa: E402
        orig_call = ClientSession.call_tool

        async def down(self, *a, **kw):
            raise ConnectionError("Amplitude 연결 끊김")
        ClientSession.call_tool = down
        try:
            script(provider, [("tool", "query_funnel", {"events": ["scan_start"]}), ("final", done)])
            evs = sse(c, c.post("/api/conversations", json={}).json()["id"])
        finally:
            ClientSession.call_tool = orig_call
        assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], evs
        assert evs[1][1]["source"] == "amplitude" and evs[2][1]["status"] == "failed", evs[2]
        assert "Amplitude 연결 끊김" in evs[2][1]["resultSummary"], evs[2]  # openai는 AgentsException으로 감쌈
        assert Message.model_validate(evs[-1][1]).status == "completed"
        ok(f"{provider}: MCP call_tool ConnectionError → tool_result failed 후 final")

    os.environ["AMPLITUDE_MCP_URL"] = "http://127.0.0.1:9/mcp"  # 닫힌 포트: 연결 자체 실패
    for provider, model in [("anthropic", "anthropic:claude-sonnet-5-5"), ("openai", "openai:gpt-6-luna")]:
        os.environ["AGENT_MODEL"] = model
        script(provider, [("final", done)])
        evs = sse(c, c.post("/api/conversations", json={}).json()["id"])
        assert evs[-1][0] == "final" and Message.model_validate(evs[-1][1]).status == "completed", evs[-1]
    ok("Amplitude 연결 실패 → 두 런타임 모두 나머지 소스로 final")
finally:
    os.environ["AGENT_MODE"] = "fake"
    os.environ.pop("AMPLITUDE_MCP_URL")
    server.should_exit = True
print("check_b7 OK")
