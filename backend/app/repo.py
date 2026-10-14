"""외부 seam: GitHub 저장소 클론·pull·HEAD, 그리고 무료 인덱스(rg). fake면 클론하지 않고 계약서 Settings 예시 값.
저장 상태는 app_settings 'repository'(계약 repository 객체 그대로)."""
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import threading

from app import db
from app.config import env, is_fake
from app.errors import ApiError

FAKE_REPO = {"headCommit": "9f3c2a1", "codeMapCommit": "9f3c2a1", "codeMapStatus": "ready", "trackedEventCount": 87,
             "screenCount": 41, "syncedAt": "2026-10-15T08:55:02.117Z", "lastError": None}
_lock = threading.Lock()  # ponytail: 프로세스 단일 락. 단일 워커라 충분 (요청 스레드와 요약 스레드가 함께 갱신)
FUNC_RE = re.compile(
    r"(?:function\s+(\w+)"
    r"|(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|\w+\s*=>|(?:React\.)?use(?:Callback|Memo)\()"
    r"|^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::[^{]+)?\{"
    r"|\b(on[A-Z]\w*)=\{\s*(?:async\s*)?\([^)]*\)\s*=>)")  # JSX 인라인 핸들러 prop: onPress={() => {
NOT_FUNC = {"if", "for", "while", "switch", "catch", "return", "function"}


def root() -> pathlib.Path:
    return pathlib.Path(env("REPOS_DIR", "/data/repos"))


def clone_dir() -> pathlib.Path:
    return root() / "repo"


def state() -> dict | None:
    return db.get_setting("repository")


def update(**fields) -> dict:
    with _lock:
        s = state() or {}
        s.update(fields)
        db.set_setting("repository", s)
        return s


def _secret_free(text: str) -> str:
    tok = env("GITHUB_TOKEN")
    return text.replace(tok, "***") if tok else text


def _git(*args: str, cwd: pathlib.Path | None = None) -> str:
    e = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    tok = env("GITHUB_TOKEN")
    if tok:  # 토큰은 URL·.git/config에 남기지 않고 요청 헤더로만 쓴다
        basic = base64.b64encode(f"x-access-token:{tok}".encode()).decode()
        e.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                 GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {basic}")
    p = subprocess.run(["git", *args], cwd=cwd, env=e, capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(_secret_free(p.stderr.strip() or p.stdout.strip()))
    return p.stdout.strip()


def _reason(stderr: str, url: str, branch: str | None) -> str:
    s = stderr.lower()
    if "authentication" in s or "could not read username" in s or "terminal prompts disabled" in s or "403" in s:
        return "GitHub 인증 실패: GITHUB_TOKEN이 없거나 만료되었습니다."
    if branch and ("remote branch" in s or "couldn't find remote ref" in s):
        return f"브랜치 {branch}를 찾을 수 없습니다."
    if "not found" in s or "does not exist" in s or "not appear to be a git repository" in s:
        return f"저장소를 찾을 수 없습니다: {url}"
    first = stderr.strip().splitlines()[-1] if stderr.strip() else "알 수 없는 오류"
    return f"저장소 동기화 실패: {first[:200]}"


def _head(d: pathlib.Path) -> str:
    return _git("rev-parse", "--short=7", "HEAD", cwd=d)


def code_files(d: pathlib.Path, glob: str | None = None) -> list[str]:
    """CODE_GLOB(기본 *.{ts,tsx,js,jsx}) 범위의 파일 목록 (ADR-19). glob을 주면 그 교집합.
    rg의 -g 여러 개는 OR라서 목록을 따로 구해 교집합한다."""
    def ls(g: str) -> set[str]:
        out = subprocess.run(["rg", "--files", "-g", g], cwd=d, capture_output=True, text=True, timeout=60).stdout
        return {l.removeprefix("./") for l in out.splitlines()}
    files = ls(env("CODE_GLOB", "*.{ts,tsx,js,jsx}"))
    return sorted(files & ls(glob) if glob else files)


def build_index(d: pathlib.Path) -> tuple[dict, int]:
    """이벤트명 → [{file, line, function}] (rg, LLM 0원) 과 화면 수. 인덱스는 REPOS_DIR/index.json에 둔다."""
    p = subprocess.run(["rg", "--no-heading", "--with-filename", "-n", "-o", "-r", "$1", "--color", "never",
                        "-g", env("CODE_GLOB", "*.{ts,tsx,js,jsx}"), "-e",
                        env("TRACK_CALL_PATTERN", r"track\(EVENTS\.(\w+)"), "."],
                       cwd=d, capture_output=True, text=True, timeout=120)
    index: dict[str, list] = {}
    lines_cache: dict[str, list[str]] = {}
    for row in p.stdout.splitlines():
        file, line, name = row.split(":", 2)
        file = file.removeprefix("./")
        if file not in lines_cache:
            lines_cache[file] = (d / file).read_text(errors="replace").splitlines()
        index.setdefault(name, []).append({"file": file, "line": int(line),
                                           "function": enclosing_function(lines_cache[file], int(line))})
    screens = sum(1 for f in d.glob(env("SCREEN_GLOB", "src/app/**/*.tsx")) if f.is_file())
    (root() / "index.json").write_text(json.dumps(index, ensure_ascii=False))
    return index, screens


def enclosing_function(lines: list[str], line: int) -> str | None:
    """ponytail: 정규식 + 줄 단위 중괄호 균형으로 감싸는 함수 추정. 문자열 속 중괄호·괄호 없는 화살표 함수는 틀릴 수 있다. 정확도가 문제면 tree-sitter로"""
    bal = 0
    for j in range(line - 1, -1, -1):
        text = lines[j]
        if j < line - 1:
            bal += text.count("{") - text.count("}")
        m = FUNC_RE.search(text)
        name = m and next((g for g in m.groups() if g), None)
        opens_block = text.count("{") > text.count("}")
        if name and name not in NOT_FUNC and (j == line - 1 or (bal > 0 and opens_block)):
            return name
    return None


def index() -> dict:
    f = root() / "index.json"
    return json.loads(f.read_text()) if f.exists() else {}


def register(url: str, branch: str | None) -> dict:
    if is_fake():
        repo = {"url": url, "branch": branch or "develop", **FAKE_REPO}
        db.set_setting("repository", repo)
        return repo
    root().mkdir(parents=True, exist_ok=True)
    tmp = root() / "repo.new"
    shutil.rmtree(tmp, ignore_errors=True)
    try:  # 새 클론이 성공해야 기존 클론을 바꾼다
        _git("clone", "--depth", "1", *(["--branch", branch] if branch else []), url, str(tmp))
    except RuntimeError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ApiError(502, "UPSTREAM_ERROR", _reason(str(e), url, branch))
    shutil.rmtree(clone_dir(), ignore_errors=True)
    tmp.rename(clone_dir())
    branch = branch or _git("rev-parse", "--abbrev-ref", "HEAD", cwd=clone_dir())
    idx, screens = build_index(clone_dir())
    repo = {"url": url, "branch": branch, "headCommit": _head(clone_dir()), "codeMapCommit": None, "codeMapStatus": "none",
            "trackedEventCount": sum(len(v) for v in idx.values()), "screenCount": screens, "syncedAt": db.now_iso(),
            "lastError": None}
    with _lock:
        db.set_setting("repository", repo)
    return repo


def sync() -> tuple[dict, bool]:
    """pull. (repository, 커밋이 바뀌었는가). 실패하면 lastError를 남기고 기존 클론·인덱스는 유지."""
    repo = state()
    if repo is None:
        raise ApiError(409, "REPOSITORY_NOT_CONFIGURED", "등록된 저장소가 없습니다. 먼저 저장소를 등록해 주세요.")
    if is_fake():
        return update(syncedAt=db.now_iso()), False
    d = clone_dir()
    try:
        _git("fetch", "--depth", "1", "origin", repo["branch"], cwd=d)
        _git("reset", "--hard", "FETCH_HEAD", cwd=d)
    except RuntimeError as e:
        reason = _reason(str(e), repo["url"], repo["branch"])
        update(lastError=reason)
        raise ApiError(502, "UPSTREAM_ERROR", reason)
    head = _head(d)
    changed = head != repo["headCommit"]
    fields = {"headCommit": head, "syncedAt": db.now_iso(), "lastError": None}
    if changed:
        idx, screens = build_index(d)
        fields.update(trackedEventCount=sum(len(v) for v in idx.values()), screenCount=screens)
    return update(**fields), changed
