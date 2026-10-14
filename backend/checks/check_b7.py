"""B7 검사: fake connect = 계약 예시 URL + 즉시 connected, 콜백 text/html, Amplitude 도구 예외·연결 실패에도 실행이 final로 끝난다.
실제 OAuth 승인은 브라우저가 필요해 여기서 다루지 않는다."""
import json
import os

from common import client, ok
from examples import AUTH_URL
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app import agent, amplitude
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


class Scripted(GenericFakeChatModel):
    def bind_tools(self, tools, **kw):
        return self


@tool
def query_funnel(events: list[str]) -> str:
    """Amplitude 퍼널 조회."""
    raise ConnectionError("Amplitude MCP 차단")


def run(script):
    agent._model = lambda: Scripted(messages=iter(script))
    cid = c.post("/api/conversations", json={}).json()["id"]
    with c.stream("POST", f"/api/conversations/{cid}/messages", json={"content": "스캔 퍼널 이탈"}) as r:
        evs, ev = [], None
        for line in r.iter_lines():
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                evs.append((ev, json.loads(line[6:])))
    return evs


done = AIMessage(content=json.dumps({"content": "Amplitude 지표 근거가 빠졌습니다. 코드·택사노미만으로 답합니다.", "proposals": []}, ensure_ascii=False))
os.environ["AGENT_MODE"] = "real"
try:
    async def amp_tools():
        return [query_funnel]
    amplitude.tools = amp_tools
    evs = run([AIMessage(content="", tool_calls=[{"name": "query_funnel", "args": {"events": ["scan_start"]}, "id": "a1"}]), done])
    assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], evs
    assert evs[1][1]["source"] == "amplitude" and evs[2][1]["status"] == "failed"
    Message.model_validate(evs[-1][1])
    ok("Amplitude 도구 예외 → tool_result failed(source amplitude), 실행은 final")

    async def amp_down():
        raise ConnectionError("MCP 연결 불가")
    amplitude.tools = amp_down
    evs = run([done])
    assert evs[-1][0] == "final" and Message.model_validate(evs[-1][1]).status == "completed"
    ok("Amplitude 도구 목록 실패 → 나머지 소스로 final")
finally:
    os.environ["AGENT_MODE"] = "fake"
print("check_b7 OK")
