"""설정·저장소·택사노미 라우트."""
import json

from fastapi import APIRouter, Request

from app import amplitude, budget, code_tools, db, repo
from app.config import env, is_fake, num
from app.errors import ApiError
from app.schemas import M

router = APIRouter(prefix="/api/settings")
PROP_TYPES = ("string", "number", "boolean")


class RepositoryIn(M):
    url: str
    branch: str | None = None


def amplitude_state() -> dict:
    return {"status": "configured" if amplitude.configured() else "missing"}


@router.get("")
def get_settings():
    t = db.get_setting("taxonomy")
    return {"repository": repo.state(),
            "taxonomy": {"eventCount": len(t["events"]), "uploadedAt": t["uploadedAt"]} if t else None,
            "amplitude": amplitude_state(),
            "models": {"agent": env("AGENT_MODEL"), "codeSummary": env("CODE_SUMMARY_MODEL")},
            "agentMode": "fake" if is_fake() else "real",
            "budget": {"limitUsd": num("LLM_BUDGET_USD", 200), "spentUsd": budget.spent()}}


@router.put("/repository")
def put_repository(body: RepositoryIn):
    if not (body.url.startswith("https://github.com/") or body.url.startswith("file://")):
        raise ApiError(400, "VALIDATION_ERROR", "url은 https://github.com/ 으로 시작해야 합니다.")
    if body.branch is not None and not body.branch.strip():
        raise ApiError(400, "VALIDATION_ERROR", "branch는 빈 문자열일 수 없습니다.")
    r = repo.register(body.url, body.branch)
    if not is_fake():
        code_tools.start_code_map()
        r = {**r, "codeMapStatus": "building"}
    return r


@router.post("/repository/sync")
def sync_repository():
    r, changed = repo.sync()
    if changed and not is_fake():
        code_tools.start_code_map()
        r = {**r, "codeMapStatus": "building"}
    return r


def _taxonomy_error(body) -> str | None:
    """첫 위반 위치와 사유. 통과하면 None."""
    if not isinstance(body, dict) or not isinstance(body.get("events"), list) or not body["events"]:
        return "events: 이벤트가 1개 이상 있는 배열이어야 합니다."
    seen = set()
    for i, e in enumerate(body["events"]):
        at = f"events[{i}]"
        if not isinstance(e, dict):
            return f"{at}: 객체여야 합니다."
        if not isinstance(e.get("name"), str) or not e["name"].strip():
            return f"{at}.name: 필수 문자열입니다."
        if e["name"] in seen:
            return f'{at}.name: "{e["name"]}"이 중복됩니다.'
        seen.add(e["name"])
        for k in ("description", "category"):
            if e.get(k) is not None and not isinstance(e[k], str):
                return f"{at}.{k}: 문자열 또는 null이어야 합니다."
        props = e.get("properties", [])
        if not isinstance(props, list):
            return f"{at}.properties: 배열이어야 합니다."
        for j, p in enumerate(props):
            pat = f"{at}.properties[{j}]"
            if not isinstance(p, dict):
                return f"{pat}: 객체여야 합니다."
            if not isinstance(p.get("name"), str) or not p["name"].strip():
                return f"{pat}.name: 필수 문자열입니다."
            if p.get("type") not in PROP_TYPES:
                return f"{pat}.type: {json.dumps(p.get('type'), ensure_ascii=False)}는 허용되지 않습니다. string, number, boolean 중 하나여야 합니다."
            if p.get("description") is not None and not isinstance(p["description"], str):
                return f"{pat}.description: 문자열 또는 null이어야 합니다."
    return None


@router.put("/taxonomy")
async def put_taxonomy(request: Request):
    try:
        body = await request.json()
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", "본문 JSON 형식이 올바르지 않습니다.")
    problem = _taxonomy_error(body)
    if problem:  # 하나라도 실패하면 기존 택사노미 유지
        raise ApiError(400, "VALIDATION_ERROR", problem)
    t = {"events": body["events"], "uploadedAt": db.now_iso()}
    db.set_setting("taxonomy", t)
    return {"eventCount": len(t["events"]), "uploadedAt": t["uploadedAt"]}
