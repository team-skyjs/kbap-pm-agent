import logging
from contextlib import asynccontextmanager
import secrets

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import conversations, db
from app.config import env
from app.errors import ApiError, err

log = logging.getLogger("app")
VERSION = "0.1.0"
OPEN_PATHS = {"/api/health", "/api/integrations/amplitude/callback"}



@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        db.init()
        conversations.fail_stale_runs()
    except Exception as e:  # DB가 없어도 서버는 뜬다. health가 degraded로 알린다
        log.error("schema init failed: %s", e)
    yield


app = FastAPI(title="kbap-pm-agent", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def auth_and_errors(request: Request, call_next):
    # 인증이 라우팅보다 먼저다(research R3): 없는 경로도 토큰이 없으면 401
    token = env("ACCESS_TOKEN")
    if token and request.method != "OPTIONS" and request.url.path not in OPEN_PATHS:
        given = request.headers.get("authorization", "")
        if not secrets.compare_digest(given, f"Bearer {token}"):
            return err(401, "UNAUTHORIZED", "접근 토큰이 없거나 일치하지 않습니다.")
    try:
        return await call_next(request)
    except Exception:  # CORS 미들웨어 안쪽에서 잡아야 500에도 CORS 헤더가 붙는다
        log.exception("unhandled")
        return err(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다.")


# 마지막에 추가한 미들웨어가 가장 바깥이다. CORS가 401·500 응답도 감싼다
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in env("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ApiError)
async def _api_error(_: Request, e: ApiError):
    return err(e.status, e.code, e.message)


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, e: RequestValidationError):
    first = e.errors()[0] if e.errors() else {}
    if first.get("type") == "json_invalid":
        return err(400, "VALIDATION_ERROR", "본문 JSON 형식이 올바르지 않습니다.")
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body") or "본문"
    return err(400, "VALIDATION_ERROR", f"{loc} 값이 올바르지 않습니다. ({first.get('msg', '')})")


@app.exception_handler(StarletteHTTPException)
async def _http(_: Request, e: StarletteHTTPException):
    # ponytail: 404 외 상태(405 등)도 계약 코드가 없어 정의되지 않은 경로로 취급
    return err(404, "NOT_FOUND", "정의되지 않은 경로입니다.")


@app.exception_handler(Exception)
async def _unhandled(_: Request, e: Exception):
    log.exception("unhandled", exc_info=e)
    return err(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다.")


@app.get("/api/health")
def health():
    try:
        db.q("SELECT 1")
        return {"status": "ok", "db": "ok", "version": VERSION}
    except Exception:
        return {"status": "degraded", "db": "error", "version": VERSION}


app.include_router(conversations.router)
