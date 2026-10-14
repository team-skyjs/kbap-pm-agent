"""B4 검사: file:// 시험 저장소 등록·동기화, 택사노미 업로드·검증 실패 시 유지, fake 저장소 응답 = 계약 예시.
컨테이너에서 실행(git·rg 필요)."""
import copy
import os
import pathlib
import subprocess
import tempfile

from common import client, ok
from examples import SETTINGS, TAXONOMY_BODY

from app import agent
from app.schemas import Repository, Settings

agent.summarize = lambda text: "요약"  # 실제 LLM 호출 금지 (요약 캐시는 check_b5에서 검사)

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["REPOS_DIR"] = str(tmp / "repos")
src = tmp / "src-repo"
(src / "src/app").mkdir(parents=True)


def git(*a):
    subprocess.run(["git", "-c", "user.email=c@c", "-c", "user.name=c", *a], cwd=src, check=True, capture_output=True)


(src / "src/app/a.tsx").write_text("""export default function A() {
  const onTap = () => {
    track(EVENTS.a, { x: 1 });
  };
  track(EVENTS.a);
  return <Button onPress={() => track(EVENTS.a)} />;
}
""")
git("init", "-b", "main")
git("add", ".")
git("commit", "-m", "init")

c = client()
r = c.post("/api/settings/repository/sync")
assert r.status_code == 409 and r.json()["error"]["code"] == "REPOSITORY_NOT_CONFIGURED", r.text
ok("미등록 sync → 409 REPOSITORY_NOT_CONFIGURED")

os.environ["AGENT_MODE"] = "real"
try:
    r = c.put("/api/settings/repository", json={"url": f"file://{src}"})
    assert r.status_code == 200, r.text
    repo = Repository.model_validate(r.json())
    assert repo.tracked_event_count == 3 and repo.screen_count == 1 and repo.branch == "main", r.json()
    assert len(repo.head_commit) == 7 and repo.last_error is None
    from app.repo import index
    assert sorted((x["line"], x["function"]) for x in index()["a"]) == [(3, "onTap"), (5, "A"), (6, "onPress")], index()
    ok("file:// 등록: trackedEventCount 3, screenCount 1, 기본 브랜치, 인덱스 함수 추정")

    head1 = repo.head_commit
    r = c.post("/api/settings/repository/sync")
    assert r.status_code == 200 and r.json()["headCommit"] == head1
    (src / "src/app/b.tsx").write_text("track(EVENTS.b);\n")
    git("add", ".")
    git("commit", "-m", "b")
    r = c.post("/api/settings/repository/sync")
    assert r.status_code == 200 and r.json()["headCommit"] != head1 and r.json()["trackedEventCount"] == 4, r.text
    assert r.json()["screenCount"] == 2
    ok("sync: 같은 커밋 유지, 새 커밋 HEAD·인덱스 반영")

    import time
    while c.get("/api/settings").json()["repository"]["codeMapStatus"] == "building":
        time.sleep(0.1)
    good = c.get("/api/settings").json()["repository"]
    r = c.put("/api/settings/repository", json={"url": f"file://{tmp}/nope"})
    assert r.status_code == 502 and r.json()["error"]["code"] == "UPSTREAM_ERROR", r.text
    assert c.get("/api/settings").json()["repository"] == good  # 실패한 교체는 기존 등록을 건드리지 않는다
    subprocess.run(["mv", str(src), str(tmp / "moved")], check=True)
    r = c.post("/api/settings/repository/sync")
    assert r.status_code == 502 and r.json()["error"]["code"] == "UPSTREAM_ERROR", r.text
    s = c.get("/api/settings").json()["repository"]
    assert s["lastError"] and s["headCommit"] == good["headCommit"], s
    ok("클론·동기화 실패 → 502 UPSTREAM_ERROR, lastError 저장, 기존 값 유지")

    os.environ["GITHUB_TOKEN"] = "ghp_SECRET_TOKEN_123"
    r = c.put("/api/settings/repository", json={"url": "https://github.com/team-skyjs/definitely-not-a-repo-xyz"})
    assert r.status_code == 502 and "ghp_SECRET_TOKEN_123" not in r.text, r.text
    ok("토큰이 에러 응답에 노출되지 않음")
finally:
    os.environ["AGENT_MODE"] = "fake"
    os.environ.pop("GITHUB_TOKEN", None)

for bad in [{"url": "https://gitlab.com/x/y"}, {"url": 3}, {}]:
    r = c.put("/api/settings/repository", json=bad)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", r.text
ok("잘못된 url → 400")

r = c.put("/api/settings/repository", json={"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop"})
assert r.status_code == 200 and r.json() == SETTINGS["repository"], r.json()
r = c.post("/api/settings/repository/sync")
assert r.json()["syncedAt"] != SETTINGS["repository"]["syncedAt"] and r.json()["headCommit"] == "9f3c2a1"
ok("fake PUT 저장소 = 계약 예시 값, fake sync는 syncedAt만 갱신")

r = c.put("/api/settings/taxonomy", json=TAXONOMY_BODY)
assert r.status_code == 200 and r.json()["eventCount"] == 2 and set(r.json()) == {"eventCount", "uploadedAt"}, r.text
bad = copy.deepcopy(TAXONOMY_BODY)
bad["events"][1]["properties"][0]["type"] = "date"
r = c.put("/api/settings/taxonomy", json=bad)
assert r.status_code == 400 and r.json()["error"] == {"code": "VALIDATION_ERROR", "message":
    'events[1].properties[0].type: "date"는 허용되지 않습니다. string, number, boolean 중 하나여야 합니다.'}, r.text
dup = copy.deepcopy(TAXONOMY_BODY)
dup["events"][1]["name"] = "scan_complete"
assert "events[1].name" in c.put("/api/settings/taxonomy", json=dup).json()["error"]["message"]
assert c.put("/api/settings/taxonomy", json={"events": []}).status_code == 400
s = c.get("/api/settings").json()
assert s["taxonomy"]["eventCount"] == 2
ok("택사노미 업로드 2개, date 타입·중복·빈 배열 → 400 + 위치, 기존 값 유지")

Settings.model_validate(s)
assert s["agentMode"] == "fake" and s["amplitude"]["status"] == "disconnected" and s["amplitude"]["connectedAt"] is None
assert set(s) == set(SETTINGS)
ok("GET /api/settings = Settings 모델")
print("check_b4 OK")
