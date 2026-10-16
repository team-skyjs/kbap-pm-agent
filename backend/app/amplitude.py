"""외부 seam: Amplitude Dashboard REST·Taxonomy API (조회 전용). 프로젝트 키 Basic 인증, 키는 env에만.
도구 두 개(amplitude_query, amplitude_context)와 메시지 전송 사전 점검(preflight). 시연 모드는 호출하지 않음."""
import datetime
import json
import logging
import time
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app import db
from app.config import env
from app.errors import ApiError, ToolError

log = logging.getLogger("app.amplitude")
ALLOWED_PATHS = {"/api/2/events/segmentation", "/api/2/funnels", "/api/2/retention",
                 "/api/2/taxonomy/event", "/api/2/taxonomy/event-property", "/api/2/taxonomy/user-property"}
CACHE_SECONDS = 900
MAX_DAYS = 90
MAX_ROWS = 31
AUTH_FAILED = "Amplitude 인증 실패"
_cache: dict = {}  # ponytail: 프로세스 메모리 캐시, 단일 워커 전제. 여러 워커면 공유 캐시(DB·Redis)로
_transport = None  # 검사 스크립트가 httpx.MockTransport로 교체


class AmplitudeError(ToolError):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind  # bad_request | auth | rate | connect


def _keys() -> tuple[str, str] | None:
    k, s = env("AMPLITUDE_API_KEY"), env("AMPLITUDE_SECRET_KEY")
    return (k, s) if k and s else None


def configured() -> bool:
    return _keys() is not None


def _read_only(request: httpx.Request) -> None:
    # 시크릿 키에는 쓰기 권한도 있어 이 클라이언트로 나가는 모든 요청을 전송 직전에 검사
    if request.method != "GET" or request.url.path not in ALLOWED_PATHS:
        raise ValueError(f"허용되지 않은 Amplitude 요청: {request.method} {request.url.path}")


def _client() -> httpx.Client:
    keys = _keys()
    if keys is None:
        raise AmplitudeError("missing", "Amplitude 키 없음")
    return httpx.Client(base_url=env("AMPLITUDE_REST_BASE") or "https://amplitude.com", auth=httpx.BasicAuth(*keys),
                        timeout=20, transport=_transport, event_hooks={"request": [_read_only]})


def _get(path: str, params: list[tuple[str, str]] | None = None):
    """허용 경로 GET + 15분 캐시. 실패는 종류별 AmplitudeError(메시지에 키·응답 헤더 없음)."""
    key = (path, tuple(params or ()))
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        with _client() as c:
            r = c.get(path, params=params or [])
    except httpx.HTTPError as e:
        log.warning("amplitude %s failed: %s", path, type(e).__name__)
        raise AmplitudeError("connect", "Amplitude 연결 실패") from None
    if r.status_code == 400:
        raise AmplitudeError("bad_request", f"Amplitude 인자 오류: {r.text[:300]}")
    if r.status_code in (401, 403):
        raise AmplitudeError("auth", AUTH_FAILED)
    if r.status_code == 429:
        raise AmplitudeError("rate", "Amplitude 요청 한도 초과(잠시 후 다시)")
    if r.status_code >= 300:
        log.warning("amplitude %s status %s", path, r.status_code)
        raise AmplitudeError("connect", "Amplitude 연결 실패")
    data = r.json()
    _cache[key] = (time.monotonic(), data)
    return data


PREFLIGHT = {"missing": "서버에 Amplitude 키가 설정되어 있지 않습니다", "auth": "인증에 실패했습니다(키 확인 필요)",
             "rate": "요청 한도를 넘었습니다(잠시 후 다시)"}


def preflight() -> None:
    """메시지 전송 전 점검: 이벤트 목록 1회(맥락 도구와 캐시 공유). 실패면 503 AMPLITUDE_UNAVAILABLE."""
    try:
        _get("/api/2/taxonomy/event")
    except AmplitudeError as e:
        reason = PREFLIGHT.get(e.kind, "연결에 실패했습니다")
        raise ApiError(503, "AMPLITUDE_UNAVAILABLE",
                       f"Amplitude 조회 불가: {reason}. 그래도 진행하면 Amplitude 없이 답합니다.") from None


# --- amplitude_query 인자: 종류에 맞지 않는 인자는 무시하지 않고 오류(모델이 원하던 것과 다른 조회를 근거로 쓰지 않게)
class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventFilter(_Strict):
    subprop_type: Literal["event", "user"]
    subprop_key: str
    subprop_op: Literal["is", "is not", "contains", "does not contain", "less", "less or equal", "greater",
                        "greater or equal"]
    subprop_value: list[str] = Field(min_length=1)


class AmplitudeEvent(_Strict):
    event_type: str = Field(description="실제 이벤트 이름. 커스텀 이벤트는 ce:이름")
    filters: list[EventFilter] = []


EVENT_COUNTS = {"segmentation": (1, 2), "funnel": (2, 10), "retention": (2, 2)}
ONLY = {"metric": {"segmentation"}, "formula": {"segmentation"}, "interval": {"segmentation", "retention"},
        "group_by": {"segmentation", "funnel"}, "n": {"segmentation", "funnel"}, "conversion_window_seconds": {"funnel"}}


class QueryArgs(_Strict):
    kind: Literal["segmentation", "funnel", "retention"]
    events: list[AmplitudeEvent]
    start: datetime.date
    end: datetime.date
    metric: Literal["uniques", "totals", "avg", "pct_dau", "formula"] | None = None
    formula: str | None = None
    interval: Literal[1, 7, 30] | None = None
    group_by: str | None = None
    n: Literal["any", "active", "new"] | None = None
    conversion_window_seconds: int | None = Field(default=None, ge=1, le=7_776_000)

    @model_validator(mode="after")
    def _rules(self):
        lo, hi = EVENT_COUNTS[self.kind]
        if not lo <= len(self.events) <= hi:
            raise ValueError(f"{self.kind}의 events는 {lo}~{hi}개입니다(받은 개수 {len(self.events)})"
                             if lo != hi else f"{self.kind}의 events는 정확히 {lo}개입니다(시작, 복귀)")
        for k, kinds in ONLY.items():
            if getattr(self, k) is not None and self.kind not in kinds:
                raise ValueError(f"{k}는 {', '.join(sorted(kinds))}에서만 씁니다")
        days = (self.end - self.start).days + 1
        if days < 1:
            raise ValueError("start가 end보다 뒤입니다")
        if days > MAX_DAYS:
            raise ValueError(f"기간 {days}일, 상한 {MAX_DAYS}일. 기간을 줄여 다시 호출")
        if self.kind == "segmentation" and self.n == "new":
            raise ValueError("세그멘테이션의 n은 any·active만 됩니다. 신규 사용자는 funnel의 n new로")
        if self.kind == "funnel" and self.n == "any":
            raise ValueError("퍼널의 n은 new·active만 됩니다")
        if (self.metric == "formula") != (self.formula is not None):
            raise ValueError("formula는 metric formula와 함께만 씁니다")
        return self


def _arg_error(e: ValidationError) -> str:
    first = e.errors()[0]
    loc = ".".join(str(p) for p in first["loc"])
    msg = first["msg"].removeprefix("Value error, ")
    return f"인자 오류: {loc + ': ' if loc else ''}{msg}"


# --- 결과 압축표: 같은 프로젝트에서 검증된 kbap-amplitude 형식을 옮김(차트 dict 제외)
def _num(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.3g}" if abs(v) < 1 else f"{v:.1f}"
    return str(v)


def _labels(data: dict, n: int) -> list[str]:
    raw = data.get("seriesLabels") or []
    # [세그먼트 인덱스, 값] 형태면 인덱스 제거
    raw = [l[1:] if isinstance(l, list) and len(l) > 1 and isinstance(l[0], int) else l for l in raw]
    return [("/".join(map(str, l)) if isinstance(l, list) else str(l)) for l in raw] or [f"s{i}" for i in range(n)]


def _summary(x: list, labels: list[str], series: list) -> str:
    out = []
    for lab, s in list(zip(labels, series))[:6]:
        vals = [v for v in s if isinstance(v, (int, float))]
        if not vals:
            continue
        mi, ma = min(vals), max(vals)
        at = x[s.index(ma)] if s.index(ma) < len(x) else ""
        out.append(f"{lab}: 합 {_num(sum(vals))} · 평균 {_num(sum(vals) / len(vals))} · 최대 {_num(ma)}({at}) "
                   f"· 최소 {_num(mi)} · 마지막 {_num(vals[-1])} · 0인 날 {sum(1 for v in vals if v == 0)}/{len(vals)}")
    return "\n".join(out)


def series_table(data: dict, title: str) -> str:
    series = data.get("series") or []
    labels = _labels(data, len(series))
    x = data.get("xValues") or []
    rows = ["| date | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
    for i, d in enumerate(x[:MAX_ROWS]):
        rows.append(f"| {d} | " + " | ".join(_num(s[i] if i < len(s) else None) for s in series) + " |")
    if len(x) > MAX_ROWS:
        rows.append(f"| … {len(x) - MAX_ROWS} rows 생략 (요약 통계는 전체 기준) |")
    return f"**{title} ({len(x)} rows × {len(series)} series)**\n" + "\n".join(rows) + "\n요약: " + _summary(x, labels, series)


def funnel_table(data, title: str) -> str:
    funnels = data if isinstance(data, list) else []
    if len(funnels) > 1:  # group_by: 세그먼트별 퍼널
        ev = funnels[0].get("events", [])
        rows = ["| segment | " + " | ".join(f"{e} (conv%)" for e in ev) + " |", "|---|" + "---|" * len(ev)]
        small = []
        for f in funnels[:MAX_ROWS]:
            seg = (f.get("meta") or {}).get("segment") or "?"
            raw, cum = f.get("cumulativeRaw", []), f.get("cumulative", [])
            cells = [_num(raw[i] if i < len(raw) else None) + (f" ({cum[i] * 100:.1f}%)" if i < len(cum) and cum[i] is not None else "")
                     for i in range(len(ev))]
            rows.append(f"| {seg} | " + " | ".join(cells) + " |")
            if raw and raw[0] < 30:
                small.append(seg)
        text = f"**{title}** 세그먼트 {len(funnels)}개\n" + "\n".join(rows)
        return text + (f"\n⚠ 1단계 표본 <30 세그먼트: {small} — 비율 해석 불가" if small else "")
    f = funnels[0] if funnels else {}
    ev, raw, cum = f.get("events", []), f.get("cumulativeRaw", []), f.get("cumulative", [])
    rows = ["| step | event | users | conv% | step conv% |", "|---|---|---|---|---|"]
    for i, e in enumerate(ev):
        c = f"{cum[i] * 100:.1f}%" if i < len(cum) and cum[i] is not None else ""
        sc = "100%" if i == 0 else (f"{raw[i] / raw[i - 1] * 100:.1f}%" if i < len(raw) and raw[i - 1] else "")
        rows.append(f"| {i + 1} | {e} | {_num(raw[i] if i < len(raw) else None)} | {c} | {sc} |")
    text = f"**{title}**\n" + "\n".join(rows)
    return text + (f"\n⚠ 1단계 표본 {raw[0]}명 (<30) — 비율 해석 불가, 절대수로 보고" if raw and raw[0] < 30 else "")


def _pct(c):
    return None if not isinstance(c, dict) or c.get("incomplete") or not c.get("outof") else round(c["count"] / c["outof"] * 100, 1)


def retention_table(data: dict, title: str) -> str:
    """series[0] = {values: {cohort: [cell]}, dates, combined: [cell]}, cell = {count, outof, incomplete}. 표본 0 코호트 생략."""
    s0 = (data.get("series") or [{}])[0]
    values, combined = s0.get("values") or {}, s0.get("combined") or []
    ndays = max([len(combined)] + [len(v) for v in values.values()])
    days = [f"D{i}" for i in range(ndays)]
    show = min(ndays, 15)  # ponytail: 코호트 표는 D0~D14만(토큰), 합산 줄은 전체 기간
    cohorts = [d for d in reversed(s0.get("dates") or list(values)) if any(c.get("outof") for c in values.get(d, []))]
    rows = ["| cohort (n) | " + " | ".join(days[:show]) + " |", "|---|" + "---|" * show]
    for d in cohorts[:MAX_ROWS]:
        cells = values[d][:show]
        rows.append(f"| {d} ({cells[0]['outof'] if cells else 0}) | " + " | ".join("" if _pct(c) is None else f"{_pct(c)}%" for c in cells) + " |")
    nout = combined[0]["outof"] if combined else 0
    avg = [(i, _pct(c), c) for i, c in enumerate(combined)]
    return (f"**{title}** 코호트 {len(cohorts)}개 (표본 0 코호트 {len(values) - len(cohorts)}개 생략), 합산 모수 n={nout}\n"
            + "\n".join(rows) + "\n합산(combined): "
            + ", ".join(f"D{i} {a}% ({c['count']}/{c['outof']})" for i, a, c in avg if a is not None and i in (0, 1, 2, 3, 7, 14, 30)))


def _event_json(e: AmplitudeEvent) -> str:
    body = {"event_type": e.event_type}
    if e.filters:
        body["filters"] = [f.model_dump() for f in e.filters]
    return json.dumps(body, ensure_ascii=False)


def amplitude_query(kind: Literal["segmentation", "funnel", "retention"], events: list[AmplitudeEvent], start: str, end: str,
                    metric: Literal["uniques", "totals", "avg", "pct_dau", "formula"] | None = None,
                    formula: str | None = None, interval: Literal[1, 7, 30] | None = None, group_by: str | None = None,
                    n: Literal["any", "active", "new"] | None = None, conversion_window_seconds: int | None = None) -> str:
    """Amplitude 지표 조회(조회 전용). 결과는 압축 마크다운 표.
    kind: segmentation(events 1~2개, metric uniques|totals|avg|pct_dau|formula, formula는 metric formula일 때만 "UNIQUES(A)/UNIQUES(B)",
    interval 1|7|30, group_by, n any|active), funnel(events 2~10개 순서대로, n new|active, conversion_window_seconds, group_by),
    retention(events 정확히 2개: 시작·복귀, interval).
    events: [{"event_type": 실제 이벤트 이름, "filters": [{"subprop_type": "event"|"user", "subprop_key", "subprop_op": "is" 등, "subprop_value": [문자열]}]}].
    start·end: YYYY-MM-DD, 양 끝 포함 90일 이내. group_by: 사용자 속성 이름 하나(커스텀은 gp:이름). 종류에 맞지 않는 인자는 오류."""
    raw = {k: v for k, v in locals().items() if v is not None}
    raw["events"] = [e.model_dump() if isinstance(e, BaseModel) else e for e in events]
    try:
        a = QueryArgs.model_validate(raw)
    except ValidationError as e:
        raise ToolError(_arg_error(e)) from None
    s, t = a.start.strftime("%Y%m%d"), a.end.strftime("%Y%m%d")
    names = ", ".join(e.event_type for e in a.events)
    title = f"{a.kind} {names} {a.start}~{a.end}"
    if a.kind == "segmentation":
        p = [("e", _event_json(a.events[0]))] + ([("e2", _event_json(a.events[1]))] if len(a.events) > 1 else [])
        p += [("m", a.metric or "uniques")] + ([("formula", a.formula)] if a.formula else [])
        p += [("start", s), ("end", t), ("i", str(a.interval or 1)), ("n", a.n or "any")] + ([("g", a.group_by)] if a.group_by else [])
        return series_table(_get("/api/2/events/segmentation", p)["data"], title)
    if a.kind == "funnel":
        p = [("e", _event_json(e)) for e in a.events]
        p += [("start", s), ("end", t), ("n", a.n or "active"), ("cs", str(a.conversion_window_seconds or 2_592_000))]
        p += [("g", a.group_by)] if a.group_by else []
        return funnel_table(_get("/api/2/funnels", p)["data"], title)
    p = [("se", _event_json(a.events[0])), ("re", _event_json(a.events[1])), ("start", s), ("end", t), ("i", str(a.interval or 1))]
    return retention_table(_get("/api/2/retention", p)["data"], title)


def _cat(c) -> str:
    return (c.get("name") or "") if isinstance(c, dict) else (c or "")


def amplitude_context(event_type: str | None = None) -> str:
    """Amplitude 이벤트 맥락. event_type 생략이면 이벤트 목록(업로드 택사노미 설명 우선, 출처 표시),
    주면 그 이벤트의 속성 표와 사용자 속성 이름 목록."""
    tax = {e["name"]: e for e in (db.get_setting("taxonomy") or {}).get("events", [])}
    if event_type is None:
        amp = {e["event_type"]: e for e in _get("/api/2/taxonomy/event").get("data", []) if e.get("event_type")}
        rows = ["| event | category | 설명 | 출처 |", "|---|---|---|---|"]
        for name in sorted(amp.keys() | tax.keys()):
            a, t = amp.get(name, {}), tax.get(name, {})
            source = "양쪽" if a and t else ("Amplitude에만" if a else "택사노미에만")
            desc = t.get("description") or a.get("description") or ""
            rows.append(f"| {name} | {t.get('category') or _cat(a.get('category'))} | {desc} | {source} |")
        return f"이벤트 {len(amp.keys() | tax.keys())}개 (Amplitude {len(amp)}, 택사노미 {len(tax)})\n" + "\n".join(rows)
    tprops = {p["name"]: p for p in tax.get(event_type, {}).get("properties", [])}
    props = _get("/api/2/taxonomy/event-property", [("event_type", event_type)]).get("data", [])
    users = _get("/api/2/taxonomy/user-property").get("data", [])
    rows = [f"**{event_type}** 이벤트 속성", "| property | type | 설명 |", "|---|---|---|"]
    for p in props:
        name = p.get("event_property", "")
        t = tprops.get(name, {})
        rows.append(f"| {name} | {t.get('type') or p.get('type') or ''} | {t.get('description') or p.get('description') or ''} |")
    for name, t in tprops.items():  # 택사노미에만 정의된 속성도 보이게
        if name not in {p.get("event_property") for p in props}:
            rows.append(f"| {name} | {t.get('type') or ''} | {t.get('description') or ''} (택사노미에만) |")
    names = sorted(u["user_property"] for u in users if u.get("user_property") and not u.get("is_hidden") and not u.get("deleted"))
    return "\n".join(rows) + "\n사용자 속성: " + (", ".join(names) or "없음")
