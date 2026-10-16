"""Amplitude REST 검사: 도구 두 개의 인자 규칙·압축표, 허용 경로·캐시, 사전 점검 503, 실행별 상태, 설정, 마이그레이션, 키 비노출.
Amplitude는 httpx.MockTransport, LLM은 llm_mock 가짜 전송. 실제 호출 없음.
실행: docker compose exec backend uv run python checks/check_b12.py"""
import base64
import io
import json
import logging
import os

import httpx

from common import client, db, ok
from examples import TAXONOMY_BODY
from llm_mock import script, sent, sse

from app import amplitude
from app.errors import ToolError

KEY, SECRET = "AMPKEY-7f3a91c2", "AMPSECRET-c0d4e8b6"
log_buf = io.StringIO()
_h = logging.StreamHandler(log_buf)
logging.getLogger().addHandler(_h)
logging.getLogger().setLevel(logging.DEBUG)
bodies: list[str] = []  # 응답 본문 모음, 끝에 키 문자열 검사

# --- 마이그레이션: 컬럼 없는 이전 DB + 이전 연결 행 → init() 두 번
db.init()
db.x("ALTER TABLE messages DROP COLUMN amplitude_status")
db.set_setting("amplitude", {"connectedAt": "2026-10-14T12:10:09.031Z"})
db.set_setting("amplitude_oauth", {"tokens": {"access_token": "old"}})
db.init()
db.init()
col = db.one("""SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'messages' AND COLUMN_NAME = 'amplitude_status'""")
assert col and col["COLUMN_TYPE"] == "enum('used','unavailable','skipped')", col
assert db.get_setting("amplitude") is None and db.get_setting("amplitude_oauth") is None
ok("init() 두 번 멱등: amplitude_status 컬럼 추가, 이전 연결 행 삭제")

c = client()
assert c.put("/api/settings/taxonomy", json=TAXONOMY_BODY).status_code == 200

# --- 가짜 Amplitude
SEG = {"data": {"series": [[10, 20, 0]], "seriesLabels": [[0, "scan_start"]], "xValues": ["2026-10-01", "2026-10-02", "2026-10-03"]}}
FUNNEL = {"data": [{"events": ["scan_start", "scan_complete"], "cumulativeRaw": [100, 41], "cumulative": [1.0, 0.41]}]}
cell = lambda n, o: {"count": n, "outof": o, "incomplete": False}  # noqa: E731
RET = {"data": {"series": [{"dates": ["2026-10-01", "2026-10-02"],
                            "values": {"2026-10-01": [cell(50, 50), cell(10, 50)], "2026-10-02": [cell(0, 0), cell(0, 0)]},
                            "combined": [cell(50, 50), cell(10, 50)]}]}}
EVENTS = {"data": [{"event_type": "scan_complete", "category": {"name": "scan"}, "description": "Amplitude 쪽 설명"},
                   {"event_type": "app_open", "category": None, "description": "앱 실행"}]}
EPROPS = {"data": [{"event_type": "scan_complete", "event_property": "success", "description": "Amplitude 쪽"},
                   {"event_type": "scan_complete", "event_property": "duration_ms", "description": "소요 시간"}]}
UPROPS = {"data": [{"user_property": "platform"}, {"user_property": "hidden_x", "is_hidden": True}]}
ROUTES = {"/api/2/events/segmentation": SEG, "/api/2/funnels": FUNNEL, "/api/2/retention": RET,
          "/api/2/taxonomy/event": EVENTS, "/api/2/taxonomy/event-property": EPROPS, "/api/2/taxonomy/user-property": UPROPS}
reqs: list[httpx.Request] = []
fail: dict = {}  # 경로 → 상태 코드 또는 "connect"
BASIC = "Basic " + base64.b64encode(f"{KEY}:{SECRET}".encode()).decode()


def handler(req: httpx.Request) -> httpx.Response:
    reqs.append(req)
    assert req.headers["authorization"] == BASIC
    f = fail.get(req.url.path)
    if f == "connect":
        raise httpx.ConnectError("refused", request=req)
    if f:
        return httpx.Response(f, json={"error": "x"})
    return httpx.Response(200, json=ROUTES[req.url.path])


amplitude._transport = httpx.MockTransport(handler)
os.environ.update(AMPLITUDE_API_KEY=KEY, AMPLITUDE_SECRET_KEY=SECRET)


def reset():
    amplitude._cache.clear()
    reqs.clear()
    fail.clear()


def tool_error(**kw) -> str:
    try:
        amplitude.amplitude_query(**kw)
    except ToolError as e:
        return str(e)
    raise AssertionError(f"인자 오류가 나야 함: {kw}")


# --- 도구: 압축표
reset()
seg = amplitude.amplitude_query(kind="segmentation", events=[{"event_type": "scan_start"}], start="2026-10-01", end="2026-10-03")
lines = seg.splitlines()
assert lines[0] == "**segmentation scan_start 2026-10-01~2026-10-03 (3 rows × 1 series)**", lines[0]
assert lines[1] == "| date | scan_start |" and lines[3] == "| 2026-10-01 | 10 |", lines[:4]
assert lines[-1] == "요약: scan_start: 합 30 · 평균 10.0 · 최대 20(2026-10-02) · 최소 0 · 마지막 0 · 0인 날 1/3", lines[-1]
p = dict(reqs[0].url.params)
assert (p["start"], p["end"], p["m"], p["i"], p["n"]) == ("20261001", "20261003", "uniques", "1", "any"), p
fun = amplitude.amplitude_query(kind="funnel", events=[{"event_type": "scan_start"}, {"event_type": "scan_complete"}],
                                start="2026-10-01", end="2026-10-14")
assert "| step | event | users | conv% | step conv% |" in fun and "| 2 | scan_complete | 41 | 41.0% | 41.0% |" in fun, fun
assert "⚠" not in fun
assert reqs[-1].url.params.get_list("e") == ['{"event_type": "scan_start"}', '{"event_type": "scan_complete"}']
assert (reqs[-1].url.params["n"], reqs[-1].url.params["cs"]) == ("active", "2592000")
FUNNEL["data"][0]["cumulativeRaw"] = [20, 5]
small = amplitude.amplitude_query(kind="funnel", events=[{"event_type": "scan_start"}, {"event_type": "scan_complete"}],
                                  start="2026-10-01", end="2026-10-13")
assert "⚠ 1단계 표본 20명 (<30) — 비율 해석 불가, 절대수로 보고" in small, small
ret = amplitude.amplitude_query(kind="retention", events=[{"event_type": "scan_start"}, {"event_type": "app_open"}],
                                start="2026-10-01", end="2026-10-02")
assert "| cohort (n) | D0 | D1 |" in ret and "| 2026-10-01 (50) | 100.0% | 20.0% |" in ret, ret
assert "표본 0 코호트 1개 생략" in ret and "2026-10-02 (" not in ret
assert ret.splitlines()[-1] == "합산(combined): D0 100.0% (50/50), D1 20.0% (10/50)", ret
ok("세그멘테이션·퍼널·리텐션 압축표 머리 행·요약 줄, 날짜 YYYYMMDD, 기본 n·cs, 표본 30 미만 경고")

# --- 도구: 인자 오류는 Amplitude 요청 0회
reset()
one_ev = [{"event_type": "scan_start"}]
two_ev = [{"event_type": "scan_start"}, {"event_type": "scan_complete"}]
cases = [
    (dict(kind="segmentation", events=one_ev, start="2026-07-01", end="2026-09-29"), "기간 91일"),
    (dict(kind="segmentation", events=one_ev, start="2026-10-01", end="2026-10-02", n="new"), "any·active"),
    (dict(kind="funnel", events=one_ev, start="2026-10-01", end="2026-10-02"), "2~10개"),
    (dict(kind="funnel", events=two_ev, start="2026-10-01", end="2026-10-02", metric="totals"), "metric는 segmentation"),
    (dict(kind="retention", events=one_ev, start="2026-10-01", end="2026-10-02"), "정확히 2개"),
    (dict(kind="segmentation", events=one_ev, start="2026-10-03", end="2026-10-01"), "start가 end보다 뒤"),
    (dict(kind="segmentation", events=one_ev, start="2026-10-01", end="2026-10-02", metric="formula"), "formula"),
    (dict(kind="segmentation", events=[{"event_type": "x", "extra": 1}], start="2026-10-01", end="2026-10-02"), "events.0.extra"),
]
for kw, want in cases:
    msg = tool_error(**kw)
    assert msg.startswith("인자 오류: ") and want in msg, (kw, msg)
assert reqs == [], reqs
ok(f"인자 오류 {len(cases)}종(91일, 세그멘테이션 n new, 퍼널 이벤트 1개, 퍼널 metric 등) → '인자 오류:' + 요청 0회")

# --- 도구: ce: 접두어·필터는 이벤트 JSON에 그대로
reset()
flt = {"subprop_type": "event", "subprop_key": "success", "subprop_op": "is", "subprop_value": ["true"]}
amplitude.amplitude_query(kind="segmentation", events=[{"event_type": "ce:my_event", "filters": [flt]}],
                          start="2026-10-01", end="2026-10-02", group_by="platform")
assert json.loads(reqs[0].url.params["e"]) == {"event_type": "ce:my_event", "filters": [flt]}, reqs[0].url.params["e"]
assert reqs[0].url.params["g"] == "platform"
ok("ce: 이벤트·filters가 요청 e JSON에 그대로, group_by → g")

# --- 호출 경계: 허용 밖 경로·쓰기 메서드는 전송 전 예외, 같은 조회 두 번째는 캐시
reset()
for call in (lambda cl: cl.post("/api/2/funnels"), lambda cl: cl.get("/api/2/users"),
             lambda cl: cl.delete("/api/2/taxonomy/event"), lambda cl: cl.put("/api/2/taxonomy/event")):
    try:
        with amplitude._client() as cl:
            call(cl)
        raise AssertionError("허용 밖 요청이 통과함")
    except ValueError as e:
        assert "허용되지 않은 Amplitude 요청" in str(e)
assert reqs == []
args = dict(kind="segmentation", events=one_ev, start="2026-10-01", end="2026-10-03")
amplitude.amplitude_query(**args)
amplitude.amplitude_query(**args)
assert len(reqs) == 1, len(reqs)
ok("허용 밖 경로·POST·DELETE·PUT은 전송 전 예외(요청 0), 같은 조회 두 번째는 캐시(요청 1회)")

# --- 도구 실패 분류
for status, want in [(400, "Amplitude 인자 오류: "), (401, "Amplitude 인증 실패"), (403, "Amplitude 인증 실패"),
                     (429, "Amplitude 요청 한도 초과(잠시 후 다시)"), (500, "Amplitude 연결 실패"), ("connect", "Amplitude 연결 실패")]:
    reset()
    fail["/api/2/events/segmentation"] = status
    try:
        amplitude.amplitude_query(**args)
        raise AssertionError(status)
    except ToolError as e:
        assert str(e).startswith(want), (status, str(e))
ok("도구 실패 400·401·403·429·5xx·연결 → 계약 문구")

# --- 맥락: 출처 세 종류, 택사노미 설명 우선
reset()
ctx = amplitude.amplitude_context()
assert "| event | category | 설명 | 출처 |" in ctx
assert "| scan_complete | scan | 메뉴판 스캔이 끝나 결과 화면에 도달했거나 실패했을 때 | 양쪽 |" in ctx, ctx
assert "| app_open |  | 앱 실행 | Amplitude에만 |" in ctx, ctx
assert "| scan_start | scan | 카메라 촬영 또는 갤러리 선택으로 스캔을 시작했을 때 | 택사노미에만 |" in ctx, ctx
props = amplitude.amplitude_context("scan_complete")
assert "| property | type | 설명 |" in props and "| success | boolean | 스캔 성공 여부 |" in props, props
assert "| duration_ms |  | 소요 시간 |" in props and "| fail_reason | string | 실패 사유 코드. 성공이면 없음 (택사노미에만) |" in props, props
assert props.splitlines()[-1] == "사용자 속성: platform", props
n = len(reqs)
amplitude.amplitude_context()
amplitude.amplitude_context("scan_complete")
assert len(reqs) == n == 3, (n, len(reqs))
ok("맥락: 출처 양쪽·Amplitude에만·택사노미에만, 택사노미 설명 우선, 속성 표 + 사용자 속성(숨김 제외), 15분 캐시")

# --- 설정·삭제된 경로
assert c.get("/api/settings").json()["amplitude"] == {"status": "configured"}
os.environ["AMPLITUDE_SECRET_KEY"] = ""
assert c.get("/api/settings").json()["amplitude"] == {"status": "missing"}
os.environ["AMPLITUDE_SECRET_KEY"] = SECRET
assert c.post("/api/integrations/amplitude/connect").status_code == 404
assert c.get("/api/integrations/amplitude/callback").status_code == 404
ok("설정 amplitude configured/missing(키 하나만 있어도 missing), connect·callback 404")


def new_conv() -> int:
    return c.post("/api/conversations", json={}).json()["id"]


def send(cid: int, **body):
    r = c.post(f"/api/conversations/{cid}/messages", json={"content": "질문", **body})
    bodies.append(r.text)
    return r


def amp_status(cid: int):
    return db.one("SELECT amplitude_status FROM messages WHERE conversation_id = %s AND role = 'assistant'", (cid,))["amplitude_status"]


done = {"content": "Amplitude 지표로 답합니다.", "proposals": []}
os.environ["AGENT_MODE"] = "real"
try:
    # --- 사전 점검: 이유 넷, 모델 호출·메시지 저장 없음
    MSG = "Amplitude 조회 불가: {}. 그래도 진행하면 Amplitude 없이 답합니다."
    for setup, reason in [(lambda: os.environ.update(AMPLITUDE_API_KEY=""), "서버에 Amplitude 키가 설정되어 있지 않습니다"),
                          (lambda: fail.update({"/api/2/taxonomy/event": 401}), "인증에 실패했습니다(키 확인 필요)"),
                          (lambda: fail.update({"/api/2/taxonomy/event": 429}), "요청 한도를 넘었습니다(잠시 후 다시)"),
                          (lambda: fail.update({"/api/2/taxonomy/event": "connect"}), "연결에 실패했습니다")]:
        reset()
        setup()
        script("anthropic", [("final", done)])
        cid = new_conv()
        r = send(cid)
        assert r.status_code == 503 and r.json() == {"error": {"code": "AMPLITUDE_UNAVAILABLE", "message": MSG.format(reason)}}, r.text
        assert sent == [] and db.one("SELECT COUNT(*) n FROM llm_usage")["n"] == 0
        assert db.one("SELECT COUNT(*) n FROM messages WHERE conversation_id = %s", (cid,))["n"] == 0
        os.environ["AMPLITUDE_API_KEY"] = KEY
    ok("사전 점검 키 없음·401·429·연결 실패 → 503 계약 문구, 모델 호출·llm_usage·메시지 0")
    r = send(new_conv(), skipAmplitude="true")
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", r.text
    ok("skipAmplitude 문자열 \"true\" → 400(엄격 타입)")

    q = {"kind": "segmentation", "events": [{"event_type": "scan_start"}], "start": "2026-10-01", "end": "2026-10-03"}
    for provider, model in [("anthropic", "anthropic:claude-sonnet-5-5"), ("openai", "openai:gpt-6-luna")]:
        os.environ["AGENT_MODEL"] = model
        # 건너뜀: 점검·도구 없음, 프롬프트 상태 문구
        reset()
        os.environ["AMPLITUDE_API_KEY"] = ""  # 키가 없어도 건너뛰면 실행
        script(provider, [("final", done)])
        cid = new_conv()
        evs = sse(c, cid)
        assert evs[-1][0] == "final" and amp_status(cid) == "skipped" and reqs == []
        prompt = json.dumps(sent[0], ensure_ascii=False)
        assert "Amplitude 없음(사용자가 건너뜀)" in prompt and "amplitude_query" not in json.dumps(sent[0].get("tools", [])), provider
        os.environ["AMPLITUDE_API_KEY"] = KEY
        # 정상: 점검 통과 → used, 도구 성공
        reset()
        script(provider, [("tool", "amplitude_query", q), ("final", done)])
        cid = new_conv()
        evs = sse(c, cid, skip_amplitude=False)
        assert [e for e, _ in evs] == ["message_created", "tool_call", "tool_result", "final"], evs
        assert evs[1][1]["source"] == "amplitude" and evs[1][1]["name"] == "amplitude_query" and evs[1][1]["input"]["kind"] == "segmentation"
        assert evs[2][1]["status"] == "succeeded" and evs[2][1]["resultSummary"].startswith("**segmentation scan_start"), evs[2]
        names = {t.get("name") for t in sent[0]["tools"]}
        assert {"amplitude_query", "amplitude_context"} <= names and "Amplitude 있음" in json.dumps(sent[0], ensure_ascii=False)
        assert amp_status(cid) == "used"
        # 실행 중 401 → unavailable, 실행은 final
        reset()
        script(provider, [("tool", "amplitude_query", q), ("final", done)])
        cid = new_conv()
        sse(c, cid, skip_amplitude=False)  # 점검 통과(캐시 채움)
        fail["/api/2/events/segmentation"] = 401
        amplitude._cache.pop(next(k for k in amplitude._cache if k[0] == "/api/2/events/segmentation"), None)
        script(provider, [("tool", "amplitude_query", q), ("final", done)])
        cid = new_conv()
        evs = sse(c, cid, skip_amplitude=False)
        assert evs[-1][0] == "final" and evs[2][1]["status"] == "failed", evs
        assert evs[2][1]["resultSummary"] == "Amplitude 인증 실패", evs[2]
        assert "Amplitude 인증 실패" in json.dumps(sent[1], ensure_ascii=False)  # 모델에도 같은 실패 문장
        assert amp_status(cid) == "unavailable"
        bodies.extend(json.dumps(d, ensure_ascii=False) for _, d in evs)
        ok(f"{provider}: skipAmplitude → skipped(프롬프트 '없음(사용자가 건너뜀)', 도구 없음), 정상 → used, 실행 중 401 → unavailable + final")
finally:
    os.environ["AGENT_MODE"] = "fake"
    os.environ["AGENT_MODEL"] = "anthropic:claude-sonnet-5-5"

# --- 시연 모드: 점검 없음, 상태 NULL
reset()
os.environ["AMPLITUDE_API_KEY"] = ""
cid = new_conv()
evs = sse(c, cid, skip_amplitude=False)
assert evs[-1][0] == "final" and amp_status(cid) is None and reqs == []
os.environ["AMPLITUDE_API_KEY"] = KEY
ok("시연 모드: 키 없어도 점검 없이 실행, amplitude_status NULL, Amplitude 요청 0")

rows = db.q("""SELECT amplitude_status, COUNT(*) AS n FROM messages WHERE role = 'assistant' AND status = 'completed'
               AND amplitude_status IS NOT NULL GROUP BY amplitude_status""")
assert {r["amplitude_status"]: r["n"] for r in rows} == {"skipped": 2, "used": 4, "unavailable": 2}, rows
ok("상태별 건수 조회 한 줄: used 4, skipped 2, unavailable 2")

# --- 비밀: 로그·응답·DB에 키 문자열 없음
stored = json.dumps(db.q("SELECT input_json, result_summary, result_text FROM tool_calls"), ensure_ascii=False, default=str)
for s in (KEY, SECRET):
    assert s not in log_buf.getvalue() and all(s not in b for b in bodies) and s not in stored, s
assert log_buf.getvalue(), "로그 캡처가 비어 있음"
ok("키 문자열이 로그·응답 본문·tool_calls에 없음")
print("check_b12 OK")
