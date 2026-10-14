"""외부 seam: Amplitude 원격 MCP (조회 전용). OAuth 2.1 + 동적 클라이언트 등록은 MCP SDK OAuthClientProvider 담당.
토큰·클라이언트 정보는 app_settings 'amplitude_oauth'에 보관(API로 노출하지 않음). 연결 상태는 'amplitude' {connectedAt}.
fake면 계약서 예시 승인 URL 반환 후 즉시 connected."""
import asyncio
import contextlib
import html
import json
import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import db
from app.config import env, is_fake
from app.errors import ApiError

log = logging.getLogger("app.amplitude")
router = APIRouter(prefix="/api/integrations/amplitude")
FAKE_AUTH_URL = ("https://app.amplitude.com/oauth/authorize?response_type=code&client_id=mcp-4f2a91&redirect_uri="
                 "https%3A%2F%2Fpm-agent-api.simhani1.dev%2Fapi%2Fintegrations%2Famplitude%2Fcallback&state=Zx81kQ"
                 "&code_challenge=Q9v0aR3&code_challenge_method=S256")
# ponytail: 진행 중 OAuth 하나를 프로세스 메모리에 보관(단일 워커, 사용자 2명). 다중 워커면 state를 DB에
_pending: dict = {}


def server_url() -> str:
    return env("AMPLITUDE_MCP_URL", "https://mcp.amplitude.com/mcp")


def connected() -> bool:
    return bool((db.get_setting("amplitude") or {}).get("connectedAt"))


def _oauth() -> dict:
    return db.get_setting("amplitude_oauth") or {}


def oauth_provider(redirect_handler=None, callback_handler=None):
    """두 LLM 런타임과 연결 흐름이 함께 쓰는 OAuth provider(httpx.Auth). 토큰 갱신은 provider가 자체 처리."""
    from mcp.client.auth import OAuthClientProvider, TokenStorage
    from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

    class DbStorage(TokenStorage):
        async def get_tokens(self):
            t = _oauth().get("tokens")
            return OAuthToken.model_validate(t) if t else None

        async def set_tokens(self, tokens):
            db.set_setting("amplitude_oauth", {**_oauth(), "tokens": tokens.model_dump(mode="json")})

        async def get_client_info(self):
            c = _oauth().get("client")
            return OAuthClientInformationFull.model_validate(c) if c else None

        async def set_client_info(self, info):
            db.set_setting("amplitude_oauth", {**_oauth(), "client": info.model_dump(mode="json")})

    redirect_uri = env("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/") + "/api/integrations/amplitude/callback"
    meta = OAuthClientMetadata(client_name="kbap-pm-agent", redirect_uris=[redirect_uri], scope="all:read",
                               grant_types=["authorization_code", "refresh_token"], response_types=["code"],
                               token_endpoint_auth_method="none")
    return OAuthClientProvider(server_url(), meta, DbStorage(), redirect_handler=redirect_handler,
                               callback_handler=callback_handler)


async def _list_tools(auth) -> list:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(server_url(), auth=auth) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            return (await s.list_tools()).tools


async def _no_browser(_url):  # 실행 중에는 재승인 불가
    raise RuntimeError("Amplitude 재승인이 필요합니다. 설정 화면에서 다시 연결해 주세요.")


DEFAULT_TOOLS = "get_amplitude_context,query_amplitude_data"


def keep(tools: list) -> list:
    """AMPLITUDE_TOOLS 허용 목록으로 MCP 도구 거르기. 빈 값이면 전부 허용(디버그용).
    서버가 내려주는 도구 전체를 매 턴 넘기면 입력 토큰·첫 응답 지연이 크게 늘어서 필요한 것만 전달."""
    allow = {n.strip() for n in env("AMPLITUDE_TOOLS", DEFAULT_TOOLS).split(",") if n.strip()}
    kept = [t for t in tools if not allow or t.name in allow]
    if allow and tools and not kept:  # 오타·서버 도구 이름 변경: 런타임이 소스 상태를 "허용 목록 불일치"로 표시
        log.warning("amplitude tools: allowlist matched 0 of %d", len(tools))
    else:
        log.info("amplitude tools: kept %d of %d", len(kept), len(tools))
    return kept


MISMATCH = "없음(허용 목록 불일치)"


@contextlib.asynccontextmanager
async def anthropic_tools():
    """Anthropic 런타임용: 실행 1회 동안 MCP 세션을 열고 (mcp Tool, ClientSession) 목록 제공. 미연결이면 [].
    연결 실패 처리는 호출자 몫. 세션은 이 컨텍스트를 연 태스크 안에서 닫아야 함(anyio 취소 범위)."""
    if is_fake() or not connected():
        yield []
        return
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(server_url(), auth=oauth_provider(redirect_handler=_no_browser)) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield [(t, session) for t in keep((await session.list_tools()).tools)]


def call_key(name: str, arguments) -> tuple[str, str]:
    return name, json.dumps(arguments or {}, sort_keys=True, ensure_ascii=False)


def openai_server(**kwargs):
    """OpenAI Agents 런타임용 MCP 서버 객체. 미연결이면 None. 같은 OAuth provider를 params["auth"]로 전달."""
    if is_fake() or not connected():
        return None
    from agents.mcp import MCPServerStreamableHttp

    class Allowlisted(MCPServerStreamableHttp):
        originals: dict = {}  # (도구 이름, 인자 JSON) → 자르기 전 원문 목록, 이벤트·DB용

        async def list_tools(self, *args, **kw):  # SDK가 턴마다 호출, 허용 목록 적용 지점은 Anthropic과 같은 keep()
            tools = await super().list_tools(*args, **kw)
            if getattr(self, "_kept", None) is None:  # 로그는 실행당 한 번
                self._kept = {t.name for t in keep(tools)}
            return [t for t in tools if t.name in self._kept]

        async def call_tool(self, tool_name, arguments, meta=None):
            # 이 경로의 MCP 결과는 공통 래퍼를 거치지 않아 여기서 모델용 사본만 자름
            from mcp.types import TextContent

            from app.agent import clip
            result = await super().call_tool(tool_name, arguments, meta)
            text = "\n".join(getattr(c, "text", "") for c in result.content)
            self.originals.setdefault(call_key(tool_name, arguments), []).append(text)
            if clip(text) == text and all(isinstance(c, TextContent) for c in result.content):
                return result
            # 이미지·오디오·리소스 블록은 상한을 우회하므로 모델 사본에서 제거, 텍스트만 하나로
            return result.model_copy(update={"content": [TextContent(type="text", text=clip(text))]})

    Allowlisted.originals = {}
    return Allowlisted(name="amplitude", cache_tools_list=True,
                                   params={"url": server_url(), "auth": oauth_provider(redirect_handler=_no_browser)},
                                   **kwargs)


@router.post("/connect")
async def connect():
    if is_fake():
        db.set_setting("amplitude", {"connectedAt": db.now_iso()})
        return {"authorizationUrl": FAKE_AUTH_URL}
    old = _pending.pop("task", None)
    if old:
        old.cancel()
    loop = asyncio.get_running_loop()
    url_fut, code_fut = loop.create_future(), loop.create_future()

    async def redirect(url: str):
        url_fut.set_result(url)

    async def callback():
        return await code_fut

    oauth = _oauth()
    db.set_setting("amplitude_oauth", {k: v for k, v in oauth.items() if k != "tokens"})  # 재승인 강제, 클라이언트 등록은 재사용
    db.del_setting("amplitude")

    async def handshake():
        await _list_tools(oauth_provider(redirect, callback))
        db.set_setting("amplitude", {"connectedAt": db.now_iso()})

    task = asyncio.create_task(handshake())
    _pending.update(task=task, code=code_fut)
    await asyncio.wait({url_fut, task}, timeout=30, return_when=asyncio.FIRST_COMPLETED)
    if url_fut.done():
        return {"authorizationUrl": url_fut.result()}
    task.cancel()
    reason = "응답 시간 초과" if not task.done() or task.cancelled() else type(task.exception()).__name__
    log.error("amplitude connect failed: %s", task.exception() if task.done() and not task.cancelled() else reason)
    raise ApiError(502, "UPSTREAM_ERROR", f"Amplitude OAuth를 시작하지 못했습니다. ({reason})")


def _page(text: str) -> HTMLResponse:
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><p>{html.escape(text)}</p>")


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    fut, task = _pending.get("code"), _pending.get("task")
    if error:
        return _page(f"Amplitude 연결 실패: {error}")
    if not code or fut is None or fut.done():
        return _page("Amplitude 연결 실패: 진행 중인 연결 요청이 없습니다. 설정 화면에서 다시 연결해 주세요.")
    fut.set_result((code, state))
    try:
        await asyncio.wait_for(asyncio.shield(task), 60)
        return _page("Amplitude 연결 완료. 이 탭을 닫아도 됩니다.")
    except Exception as e:
        log.exception("amplitude token exchange failed")
        return _page(f"Amplitude 연결 실패: {type(e).__name__}")
