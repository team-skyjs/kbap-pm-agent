"""질문 다듬기 검사: 시연 모드 응답·기록, 요청 검증, 예산, ENUM 마이그레이션 멱등성, 프롬프트 규칙, 입력 조립,
두 런타임 가짜 전송(성공·거절·잘못된 JSON), 선택 기록·덮어쓰기·집계. 실제 LLM 호출 없음."""
import os
import re
import time

from common import client, ok
from examples import REFINE, REFINE_CHOICE, TAXONOMY_BODY
from llm_mock import script, sent

from app import db
from app.refine import NAMES_MAX_CHARS, REFINE_PROMPT, TRUNCATED_NOTE, build_prompt, with_truncated_note

c = client()


def refinements() -> int:
    return db.one("SELECT COUNT(*) AS n FROM question_refinements")["n"]


def refine_usage() -> int:
    return db.one("SELECT COUNT(*) AS n FROM llm_usage WHERE purpose = 'refine'")["n"]


# --- 시연 모드 응답·기록
r = c.post("/api/questions/refine", json={"conversationId": None, "question": "스캔 이탈 왜 많아?"})
assert r.status_code == 200, r.text
body = r.json()
assert set(body) == set(REFINE) and isinstance(body["refinementId"], int) and body["refinementId"] > 0, body
assert body["refined"] == REFINE["refined"] and body["summary"] == REFINE["summary"], body
assert refinements() == 1 and refine_usage() == 1
assert db.one("SELECT cost_usd, model FROM llm_usage WHERE purpose = 'refine'") == {"cost_usd": 0, "model": "fake"}
ok("fake: 응답 키·refined·summary = 계약 예시, 기록 1행, llm_usage refine 0원 1행")

# --- 요청 검증
for bad in [{"conversationId": None, "question": ""}, {"conversationId": None, "question": "   "},
            {"conversationId": None, "question": "가" * 4001}, {"conversationId": None}, {"question": 3},
            {"conversationId": "7", "question": "x"}, {"conversationId": True, "question": "x"},
            {"conversationId": 7.5, "question": "x"}]:
    r = c.post("/api/questions/refine", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", (bad, r.text)
r = c.post("/api/questions/refine", json={"conversationId": 999999, "question": "x"})
assert r.status_code == 404 and r.json()["error"]["code"] == "CONVERSATION_NOT_FOUND", r.text
cid = c.post("/api/conversations", json={}).json()["id"]
assert c.post("/api/questions/refine", json={"conversationId": cid, "question": "x"}).status_code == 200
assert c.post("/api/questions/refine", json={"question": "conversationId 생략"}).status_code == 200
assert refinements() == 3  # 실패 요청은 행을 만들지 않음
ok("검증: 빈·공백만·4001자·누락·타입·문자열·불리언 ID 400, 없는 대화 404, 대화 있음·null·생략 200, 실패는 행 없음")

# --- 예산
os.environ["LLM_BUDGET_USD"] = "0"
try:
    r = c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "BUDGET_EXCEEDED", r.text
finally:
    os.environ.pop("LLM_BUDGET_USD")
ok("LLM_BUDGET_USD=0 → 403 BUDGET_EXCEEDED")

# --- 마이그레이션: 옛 ENUM 테이블에서 init() 두 번
db.x("DROP TABLE llm_usage")
db.x("""CREATE TABLE llm_usage (id BIGINT AUTO_INCREMENT PRIMARY KEY, message_id BIGINT NULL,
        purpose ENUM('agent','code_summary') NOT NULL, model VARCHAR(100) NOT NULL, input_tokens INT NOT NULL,
        output_tokens INT NOT NULL, cost_usd DECIMAL(10,4) NOT NULL, created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3))""")
db.init()
db.init()
col = db.one("""SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'llm_usage' AND COLUMN_NAME = 'purpose'""")["COLUMN_TYPE"]
assert "'refine'" in col, col
ok("마이그레이션: 옛 ENUM → init() 두 번(두 번째 무에러) 후 refine 포함")

# --- 프롬프트 규칙 문장
for rule in ['사용자의 의도를 바꾸지 않는다.',
             '기간, 대상 이벤트(아래 목록에 있는 실제 이름만), 보고 싶은 지표, 원하는 산출물(개선안인지 측정 설계인지)을 드러낸다.',
             "목록에 없는 이벤트 이름이나 원문에 없는 사실을 지어내지 않는다. 질문의 대상 이벤트가 택사노미에 없으면 대상을 바꾸거나 비슷해 보이는 이벤트로 대신하지 말고 원문 표현을 유지하며, 요약에 '택사노미에 없는 이벤트'라고 적는다. 이 사실은 요약에만 적고 다듬은 질문에는 쓰지 않는다.",
             '정보가 없으면 합리적 기본값(예: 최근 7일)을 쓰되 요약에 "(원문에 없음)"으로 밝힌다.',
             "기간·이벤트·지표·산출물이 이미 분명하면 문장을 거의 바꾸지 않고 요약에 '거의 그대로'라고 적는다. 없는 조건을 추가하지 않는다.",
             '다듬은 질문은 한국어(한글)로만 두 문장 이내로 쓰고, 요약은 한 줄이다.',
             '개선된 질문은 4,000자 이내로 쓴다.',
             '처리 메모·설명은 summary에만 쓰고 refined에는 질문 문장만 쓴다. 규칙 문구를 질문에 옮겨 쓰지 않는다.']:
    assert rule in REFINE_PROMPT, rule
assert "refined: 에이전트에게 보낼 질문 문장만(처리 메모·설명 없이)." in build_prompt("x", None)[0]
from app.schemas import RefineResult  # noqa: E402
props = RefineResult.model_json_schema(by_alias=True)["properties"]
assert "처리 메모" in props["refined"]["description"] and "처리 메모" in props["summary"]["description"]
assert REFINE_PROMPT.count("\n9. ") == 0 and "\n8. " in REFINE_PROMPT  # 겹치던 규칙을 합쳐 여덟 개
ok("REFINE_PROMPT: 규칙 문장 여덟 개(겹침 합침, 대체 금지·요약에만·한글만), 출력 형식과 구조화 출력 설명에 '처리 메모는 summary에만'")

# --- 입력 조립
p, truncated = build_prompt("질문입니다", None)
assert not truncated and "택사노미 없음" in p and "이력 없음" in p and p.rstrip().endswith("summary: 무엇이 달라졌는지와 처리 메모 한 줄.")
c.put("/api/settings/taxonomy", json=TAXONOMY_BODY)
cid = c.post("/api/conversations", json={}).json()["id"]
for i, (role, status, text) in enumerate([("user", "completed", "옛질문"), ("assistant", "completed", "옛답"),
                                          ("user", "completed", "가" * 600), ("assistant", "failed", "실패답"),
                                          ("assistant", "completed", "나" * 600), ("user", "completed", "최근질문"),
                                          ("assistant", "completed", ""), ("assistant", "completed", "최근답")]):
    db.x("INSERT INTO messages (conversation_id, role, status, content, created_at) VALUES (%s,%s,%s,%s, NOW(3) + INTERVAL %s SECOND)",
         (cid, role, status, text, i))
p, _ = build_prompt("그걸 주 단위로", cid)
assert "scan_complete, scan_start" in p and "스캔 성공 여부" not in p and "메뉴판 스캔이" not in p, "택사노미는 이름만"
hist = p.split("## 직전 대화(오래된 순)\n")[1].split("\n\n## 다듬을 질문")[0].splitlines()
assert hist == ["[사용자] " + "가" * 500, "[에이전트] " + "나" * 500, "[사용자] 최근질문", "[에이전트] 최근답"], hist
assert "옛질문" not in p and "실패답" not in p and p.split("## 다듬을 질문\n")[1].startswith("그걸 주 단위로")
ok("조립: 택사노미 이름만, 이력 역할별 최근 2개·500자·오래된 순, 실패·빈 메시지 제외, 질문은 마지막")

# --- 택사노미 이름 4,000자 상한: 앞에서 자르고 서버가 요약 끝에 표시(300자 이내)
big = {"events": [{"name": f"event_{i:04d}_" + "x" * 30, "description": None, "category": None, "properties": []}
                  for i in range(300)]}
assert c.put("/api/settings/taxonomy", json=big).status_code == 200
p, truncated = build_prompt("질문", None)
names_line = p.split("## 택사노미 이벤트 이름\n")[1].split("\n")[0]
assert truncated and len(names_line) <= NAMES_MAX_CHARS and names_line.startswith("event_0000_"), len(names_line)
assert "event_0299_" not in names_line and names_line.split(", ")[-1].startswith("event_")  # 이름 중간에서 끊지 않음
r = c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
assert r.status_code == 200 and r.json()["summary"] == REFINE["summary"] + TRUNCATED_NOTE, r.json()["summary"]
assert len(with_truncated_note("요" * 300)) == 300 and with_truncated_note("요" * 300).endswith(TRUNCATED_NOTE)
# 관련 이름 우선: 맨 뒤 관련 이벤트가 잘리지 않고 앞으로
big["events"].append({"name": "cart_checkout_special", "description": None, "category": None, "properties": []})
assert c.put("/api/settings/taxonomy", json=big).status_code == 200
p, truncated = build_prompt("cart 이탈 왜 많아?", None)
names_line = p.split("## 택사노미 이벤트 이름\n")[1].split("\n")[0]
assert truncated and names_line.startswith("cart_checkout_special, event_0000_") and len(names_line) <= NAMES_MAX_CHARS, names_line[:60]
assert not build_prompt("관련 없는 질문", None)[0].split("## 택사노미 이벤트 이름\n")[1].startswith("cart_")
big["events"].append({"name": "scan_complete", "description": None, "category": None, "properties": []})
assert c.put("/api/settings/taxonomy", json=big).status_code == 200
p, truncated = build_prompt("scan_complete 왜 줄었어?", None)
names_line = p.split("## 택사노미 이벤트 이름\n")[1].split("\n")[0]
assert truncated and "scan_complete" in names_line.split(", ") and len(names_line) <= NAMES_MAX_CHARS, names_line[:80]
assert "cart_checkout_special" not in names_line.split(", ")[:1]  # 겹치지 않는 이름은 앞으로 오지 않음
c.put("/api/settings/taxonomy", json=TAXONOMY_BODY)
assert build_prompt("질문", None)[1] is False
ok("상한: 이름 4,000자 이하·truncated, fake 요약 끝에 고정 문구, 긴 요약도 300자 이내, 질문 관련 이름이 맨 뒤여도 먼저, 작은 택사노미는 표시 없음")

# --- 두 런타임 가짜 전송
os.environ["AGENT_MODE"] = "real"
os.environ["AGENT_MODEL"] = "anthropic:claude-sonnet-5-5"
os.environ["CODE_SUMMARY_MODEL"] = "anthropic:claude-haiku-5-5"
answer = {"refined": "최근 7일 scan_start 대비 scan_complete 전환율을 보여줘.", "summary": "기간을 최근 7일로 정했다(원문에 없음)."}
try:
    for provider, model in [("anthropic", "anthropic:claude-haiku-5-5"), ("openai", "openai:gpt-6-luna")]:
        os.environ["REFINE_MODEL"] = model
        before_rows, before_usage = refinements(), refine_usage()
        script(provider, [("final", answer)])
        r = c.post("/api/questions/refine", json={"conversationId": None, "question": "전환율"})
        assert r.status_code == 200 and r.json()["refined"] == answer["refined"], r.text
        assert refinements() == before_rows + 1 and refine_usage() == before_usage + 1
        assert db.one("SELECT model FROM question_refinements ORDER BY id DESC LIMIT 1")["model"] == model
        u = db.one("SELECT model, input_tokens FROM llm_usage WHERE purpose = 'refine' ORDER BY id DESC LIMIT 1")
        assert u["model"] == model and u["input_tokens"] > 0, u
        too_long = ("final", {"refined": "가" * 4001, "summary": "길이 초과"})  # 보낼 수 없는 개선안은 내보내지 않음
        blank = ("final", {"refined": "  \n\t ", "summary": "공백만"})
        for step in ([("refusal",)] if provider == "anthropic" else []) + [("raw", "JSON 아님"), too_long, blank]:
            before, before_usage = refinements(), refine_usage()
            script(provider, [step])
            r = c.post("/api/questions/refine", json={"conversationId": None, "question": "전환율"})
            assert r.status_code == 502 and r.json()["error"]["code"] == "UPSTREAM_ERROR", (provider, step, r.text)
            assert refinements() == before, "실패면 기록 행 없음"
            assert refine_usage() == before_usage + 1, (provider, step[0], "형식 오류·거절도 쓴 토큰은 사용량에 기록")
        if provider == "anthropic":  # 거절도 과금: 다듬기 행은 없지만 사용량 행은 남음
            before_usage = refine_usage()
            script(provider, [("refusal",)])
            assert c.post("/api/questions/refine", json={"conversationId": None, "question": "x"}).status_code == 502
            u = db.one("SELECT model, input_tokens, output_tokens FROM llm_usage WHERE purpose = 'refine' ORDER BY id DESC LIMIT 1")
            assert refine_usage() == before_usage + 1 and u == {"model": model, "input_tokens": 100, "output_tokens": 10}, u
        ok(f"{provider}: RefineResult 반환·기록·usage 행, " + ("거절(사용량 기록)·" if provider == "anthropic" else "")
           + "잘못된 JSON·4,001자·공백만 개선안 502 행 없음, 실패한 호출도 사용량 1행")
    os.environ.pop("REFINE_MODEL")
    script("anthropic", [("final", answer)])
    c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
    assert db.one("SELECT model FROM question_refinements ORDER BY id DESC LIMIT 1")["model"] == "anthropic:claude-haiku-5-5"
    assert "thinking" not in sent[0] and sent[0]["output_config"]["effort"] == "low", sent[0]  # 기본 adaptive: 생략
    os.environ["REFINE_THINKING"] = "disabled"
    script("anthropic", [("final", answer)])
    c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
    assert sent[0]["thinking"] == {"type": "disabled"}, sent[0]
    # disabled를 거부(400)하는 모델: adaptive로 1회 재시도해 성공
    script("anthropic", [("http400",), ("final", answer)])
    r = c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
    assert r.status_code == 200 and len(sent) == 2, (r.text, len(sent))
    assert sent[0]["thinking"] == {"type": "disabled"} and "thinking" not in sent[1]
    script("anthropic", [("http400",), ("http400",)])  # 재시도도 실패하면 502, 재시도는 1회만
    r = c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
    assert r.status_code == 502 and len(sent) == 2, (r.text, len(sent))
    os.environ["REFINE_THINKING"] = "adaptive"
    script("anthropic", [("final", answer)])
    c.post("/api/questions/refine", json={"conversationId": None, "question": "x"})
    assert "thinking" not in sent[0]
    os.environ.pop("REFINE_THINKING")
    ok("REFINE_MODEL 비면 CODE_SUMMARY_MODEL 사용, REFINE_THINKING=disabled일 때만 thinking disabled 전송, 400이면 adaptive 1회 재시도(재실패 502)")
    os.environ["REFINE_MODEL"] = "foo:bar"
    from app import agent
    try:
        agent.check_models()
        raise AssertionError("잘못된 REFINE_MODEL 접두사가 통과")
    except ValueError:
        pass
    ok("REFINE_MODEL 잘못된 접두사 → 기동 검사 실패")
finally:
    os.environ["AGENT_MODE"] = "fake"
    os.environ.pop("REFINE_MODEL", None)

# --- 선택 기록
rid = c.post("/api/questions/refine", json={"conversationId": None, "question": "x"}).json()["refinementId"]
r = c.post(f"/api/questions/refine/{rid}/choice", json={"choice": "original"})
assert r.status_code == 200 and set(r.json()) == set(REFINE_CHOICE) and r.json()["choice"] == "original", r.text
first = r.json()["chosenAt"]
time.sleep(0.01)
r = c.post(f"/api/questions/refine/{rid}/choice", json={"choice": "refined"})
assert r.json()["choice"] == "refined" and r.json()["chosenAt"] > first and r.json()["chosenAt"].endswith("Z"), r.json()
assert db.one("SELECT choice FROM question_refinements WHERE id = %s", (rid,))["choice"] == "refined"
r = c.post("/api/questions/refine/999999/choice", json={"choice": "refined"})
assert r.status_code == 404 and r.json()["error"]["code"] == "REFINEMENT_NOT_FOUND", r.text
for bad in [{"choice": "maybe"}, {}]:
    r = c.post(f"/api/questions/refine/{rid}/choice", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", r.text
ok("선택: 응답 키 = 계약 예시, 덮어쓰기와 chosenAt 갱신, 404 REFINEMENT_NOT_FOUND, 400")

# --- 채택 비율 집계(data-model.md 쿼리 그대로)
db.x("DELETE FROM question_refinements")
for choice in ["refined", "refined", "original", "cancelled"]:
    rid = c.post("/api/questions/refine", json={"conversationId": None, "question": "x"}).json()["refinementId"]
    c.post(f"/api/questions/refine/{rid}/choice", json={"choice": choice})
c.post("/api/questions/refine", json={"conversationId": None, "question": "선택 전"})
agg = db.one("""SELECT ROUND(100 * SUM(choice = 'refined') / COUNT(*), 1) AS adopted_pct, COUNT(*) AS shown
FROM question_refinements WHERE choice IS NOT NULL;""")
assert float(agg["adopted_pct"]) == 50.0 and agg["shown"] == 4, agg
ok("집계: refined 2·original 1·cancelled 1(+선택 전 1) → 채택 50.0%, shown 4")
# 두 문장 이내는 프롬프트 규칙으로만 강제(한국어 문장 분리가 불안정). 저장된 개선안 중 세 문장 이상은 경고만
long = [r["refined_question"][:40] for r in db.q("SELECT refined_question FROM question_refinements")
        if len([x for x in re.split(r"[.?!。]\s*", r["refined_question"]) if x.strip()]) > 2]
print(f"WARN 세 문장 이상 개선안 {len(long)}건" if long else "PASS 저장된 개선안 모두 두 문장 이내(경고 항목)")
print("check_b10 OK")
