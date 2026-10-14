"""B5 검사: read_code 200줄 상한, search_code 30건 상한, 요약 캐시(같은 커밋 0회·파일 1개 변경 1회), 예산 403.
컨테이너에서 실행(git·rg 필요). 요약 LLM은 기록만 하는 가짜로 바꿔 비용을 쓰지 않는다."""
import os
import pathlib
import subprocess
import tempfile
import time

from common import client, ok

from app import agent, budget, code_tools, db

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["REPOS_DIR"] = str(tmp / "repos")
src = tmp / "src-repo"
(src / "src/app").mkdir(parents=True)


def git(*a):
    subprocess.run(["git", "-c", "user.email=c@c", "-c", "user.name=c", *a], cwd=src, check=True, capture_output=True)


(src / "src/app/long.tsx").write_text("".join(f"const x{i} = {i}; // needle\n" for i in range(1, 251)))
(src / "src/app/b.tsx").write_text("export default function B() { track(EVENTS.b); }\n")
(src / "notes.md").write_text("needle\n" * 5)  # CODE_GLOB 밖
git("init", "-b", "main")
git("add", ".")
git("commit", "-m", "init")

calls = []
agent.summarize = lambda text: (calls.append(1), budget.record("code_summary", "test-model", 10, 5, None), "요약")[2]


def usage_rows() -> int:
    return db.one("SELECT COUNT(*) AS n FROM llm_usage")["n"]


def wait_map(c):
    for _ in range(100):
        r = c.get("/api/settings").json()["repository"]
        if r["codeMapStatus"] != "building":
            return r
        time.sleep(0.1)
    raise AssertionError("codeMapStatus가 building에서 끝나지 않음")


c = client()
os.environ["AGENT_MODE"] = "real"
try:
    r = c.put("/api/settings/repository", json={"url": f"file://{src}"})
    assert r.status_code == 200 and r.json()["codeMapStatus"] == "building" and r.json()["codeMapCommit"] is None, r.text
    m = wait_map(c)
    assert m["codeMapStatus"] == "ready" and m["codeMapCommit"] == m["headCommit"] and usage_rows() == 2, (m, usage_rows())
    ok("등록 → building → ready, 화면 2개 요약 2회 기록")

    out = code_tools.read_code("src/app/long.tsx", 1, 201)
    assert len(out.splitlines()) == 1 + 200 and out.splitlines()[0].endswith("(200줄)"), out.splitlines()[0]
    try:
        code_tools.read_code("../../etc/passwd", 1, 5)
        raise AssertionError("저장소 밖 경로가 거부되지 않음")
    except ValueError:
        pass
    try:
        code_tools.read_code("notes.md", 1, 5)
        raise AssertionError("CODE_GLOB 밖 파일이 거부되지 않음")
    except ValueError:
        pass
    ok("read_code 201줄 요청 → 200줄, 저장소 밖·CODE_GLOB 밖 경로 거부")

    out = code_tools.search_code("needle")
    assert len(out.splitlines()) == 1 + 30 and out.startswith("250건 중 30건"), out.splitlines()[0]
    assert code_tools.search_code("needle", "src/app/**").startswith("250건 중 30건")
    assert code_tools.search_code("needle", "notes.md").startswith("0건")
    assert code_tools.find_event_calls("b").startswith("1곳: src/app/b.tsx:1 (B)")
    assert "요약" in code_tools.get_screen_summary("src/app/b.tsx")
    ok("search_code 250건 → 30건, find_event_calls, get_screen_summary 캐시")

    before = usage_rows()
    r = c.post("/api/settings/repository/sync")
    assert r.json()["codeMapStatus"] == "ready"
    time.sleep(0.3)
    assert usage_rows() == before
    ok("같은 커밋 재동기화 → 요약 호출 0회")

    (src / "src/app/b.tsx").write_text("export default function B() { track(EVENTS.b); track(EVENTS.c); }\n")
    git("commit", "-am", "b2")
    r = c.post("/api/settings/repository/sync")
    assert r.json()["codeMapStatus"] == "building"
    m = wait_map(c)
    assert m["codeMapStatus"] == "ready" and m["codeMapCommit"] == m["headCommit"] and usage_rows() == before + 1, usage_rows()
    ok("파일 1개 변경 → 요약 1회, codeMapCommit 갱신")
finally:
    os.environ["AGENT_MODE"] = "fake"

s = c.get("/api/settings").json()["budget"]
assert s["spentUsd"] == round(3 * budget.cost("test-model", 10, 5), 4) and s["limitUsd"] == 200
assert budget.cost("anthropic:claude-sonnet-5-5", 1_000_000, 1_000_000) == 12.0
ok("spentUsd = llm_usage 합계, 단가표")

os.environ["LLM_BUDGET_USD"] = "0.01"
try:
    db.x("INSERT INTO llm_usage (purpose, model, input_tokens, output_tokens, cost_usd) VALUES ('agent','x',0,0,0.01)")
    cid = c.post("/api/conversations", json={}).json()["id"]
    r = c.post(f"/api/conversations/{cid}/messages", json={"content": "예산 시험"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "BUDGET_EXCEEDED", r.text
    assert c.get(f"/api/conversations/{cid}").status_code == 200 and c.get("/api/conversations").status_code == 200
    ok("LLM_BUDGET_USD=0.01 → 메시지 403 BUDGET_EXCEEDED, 조회는 200")
finally:
    os.environ.pop("LLM_BUDGET_USD")
print("check_b5 OK")
