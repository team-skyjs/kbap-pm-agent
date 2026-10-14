"""에이전트 도구(코드·택사노미)와 화면 요약 캐시 (ADR-9). 모델 호출은 agent.summarize()만 거친다(원칙 III).
도구는 문자열을 돌려주고 첫 줄이 요약(resultSummary)이다. 파일 통째 전송 도구는 없다(원칙 IV)."""
import json
import logging
import pathlib
import subprocess
import threading

from app import agent, budget, db, repo
from app.config import env
from app.errors import ApiError

log = logging.getLogger("app.code_tools")
MAX_READ_LINES = 200
MAX_SEARCH_HITS = 30
SUMMARY_INPUT_CHARS = 12000  # ponytail: 화면 파일 앞부분만 요약에 보낸다. 큰 화면이 잘리면 함수 단위 분할로


def _cache_file() -> pathlib.Path:
    return repo.root() / "summaries.json"


def _cache() -> dict:
    f = _cache_file()
    return json.loads(f.read_text()) if f.exists() else {}


def _safe_path(path: str) -> pathlib.Path:
    base = repo.clone_dir().resolve()
    p = (base / path).resolve()
    if not p.is_relative_to(base) or not p.is_file() or str(p.relative_to(base)) not in repo.code_files(base):
        raise ValueError(f"저장소 안의 코드 파일(CODE_GLOB)이 아닙니다: {path}")
    return p


# --- 코드 도구 (source: code)
def find_event_calls(eventName: str) -> str:
    """이벤트를 보내는 코드 위치(파일·줄·함수)를 인덱스에서 찾는다. LLM 비용 0."""
    hits = repo.index().get(eventName, [])
    if not hits:
        return f"0곳: 코드에서 {eventName} 호출을 찾지 못했습니다."
    locs = [f"{h['file']}:{h['line']} ({h['function'] or '최상위'})" for h in hits]
    return f"{len(hits)}곳: " + ", ".join(locs)


def search_code(regex: str, glob: str | None = None) -> str:
    """저장소에서 정규식으로 코드 줄을 찾는다(최대 30건). glob 예: 'src/app/**/*.tsx'."""
    files = repo.code_files(repo.clone_dir(), glob)  # CODE_GLOB 범위만 (ADR-19)
    if not files:
        return f"0건: /{regex}/ (대상 코드 파일 없음)"
    cmd = ["rg", "--no-heading", "--with-filename", "-n", "--color", "never", "-e", regex, "--", *files]
    p = subprocess.run(cmd, cwd=repo.clone_dir(), capture_output=True, text=True, timeout=60)
    if p.returncode > 1:
        raise ValueError(p.stderr.strip()[:300])
    lines = [l.removeprefix("./")[:300] for l in p.stdout.splitlines()]
    shown = lines[:MAX_SEARCH_HITS]
    head = f"{len(lines)}건 중 {len(shown)}건" if len(lines) > MAX_SEARCH_HITS else f"{len(lines)}건"
    return "\n".join([f"{head}: /{regex}/", *shown])


def get_screen_summary(path: str) -> str:
    """화면 파일의 캐시된 요약(역할·컴포넌트·핸들러·이벤트)."""
    _safe_path(path)
    blob = _blobs().get(path)
    text = _cache().get(f"{path}@{blob}")
    return f"{path} 요약\n{text}" if text else f"{path}: 요약이 아직 없습니다. read_code로 필요한 구간만 읽으세요."


def read_code(path: str, startLine: int, endLine: int) -> str:
    """파일의 줄 범위를 읽는다(1부터, 호출당 최대 200줄)."""
    lines = _safe_path(path).read_text(errors="replace").splitlines()
    start = max(1, startLine)
    end = min(endLine, start + MAX_READ_LINES - 1, len(lines))
    body = [f"{i}: {lines[i - 1]}" for i in range(start, end + 1)]
    return "\n".join([f"{path}:{start}-{end} ({len(body)}줄)", *body])


# --- 택사노미 도구 (source: taxonomy)
def _events() -> list[dict]:
    t = db.get_setting("taxonomy")
    return t["events"] if t else []


def search_taxonomy(query: str) -> str:
    """택사노미 정의에서 이벤트명·설명·카테고리에 query가 들어간 이벤트를 찾는다."""
    if not _events():
        return "택사노미가 업로드되지 않았습니다."
    q = query.lower()
    hits = [e for e in _events() if q in json.dumps(e, ensure_ascii=False).lower()]
    return "\n".join([f"일치 이벤트 {len(hits)}개: " + ", ".join(e["name"] for e in hits),
                      *(f"- {e['name']}: {e.get('description') or ''}" for e in hits[:30])])


def get_event_definition(name: str) -> str:
    """이벤트 하나의 정의(설명·속성)와 코드 존재 여부."""
    e = next((e for e in _events() if e["name"] == name), None)
    in_code = bool(repo.index().get(name))
    if e is None:
        return f"{name}: 택사노미에 정의가 없습니다" + (" (코드에만 존재, 정의 없음)" if in_code else "")
    note = "" if in_code else " (정의는 있으나 코드에서 발견되지 않음)"
    return f"{name} 정의{note}\n" + json.dumps(e, ensure_ascii=False)


CODE_TOOLS = [find_event_calls, search_code, get_screen_summary, read_code]
TAXONOMY_TOOLS = [search_taxonomy, get_event_definition]


# --- 화면 요약 캐시: 키 (path, blob SHA), 바뀐 blob만 다시 요약
def _blobs() -> dict[str, str]:
    out = subprocess.run(["git", "ls-tree", "-r", "HEAD"], cwd=repo.clone_dir(), capture_output=True, text=True).stdout
    return {line.split("\t", 1)[1]: line.split()[2] for line in out.splitlines() if "\t" in line}


def build_code_map() -> None:
    d = repo.clone_dir()
    head = repo.state()["headCommit"]
    repo.update(codeMapStatus="building")
    try:
        blobs, cache = _blobs(), _cache()
        screens = sorted(str(f.relative_to(d)) for f in d.glob(env("SCREEN_GLOB", "src/app/**/*.tsx")) if f.is_file())
        for path in screens:
            key = f"{path}@{blobs.get(path)}"
            if key in cache:
                continue
            budget.check()
            cache[key] = agent.summarize((d / path).read_text(errors="replace")[:SUMMARY_INPUT_CHARS])
            _cache_file().write_text(json.dumps(cache, ensure_ascii=False))
        repo.update(codeMapStatus="ready", codeMapCommit=head, lastError=None)
    except ApiError as e:
        repo.update(codeMapStatus="failed", lastError=f"화면 요약 중단: {e.message}")
    except Exception as e:
        log.exception("code map failed")
        repo.update(codeMapStatus="failed", lastError=f"화면 요약 실패: {str(e)[:200]}")


_running = threading.Lock()


def start_code_map() -> None:
    """동기화 직후 백그라운드로 요약 갱신. 이미 돌고 있으면 건너뛴다."""
    def run():
        with _running:
            build_code_map()
    if not _running.locked():
        repo.update(codeMapStatus="building")
        threading.Thread(target=run, daemon=True).start()
