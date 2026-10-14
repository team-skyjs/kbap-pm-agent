"""외부 seam: 모든 LLM 호출. run_agent(에이전트 실행 → 내부 이벤트)와 summarize(코드 요약).
내부 이벤트(dict):
  {"type": "tool_call", "key", "source", "name", "input"}
  {"type": "tool_result", "key", "status": "succeeded"|"failed", "summary", "text"}
  {"type": "final", "content", "proposals": [ProposalDraft 별칭 dict]}
  {"type": "error", "code", "message"}
DB 저장과 SSE 변환은 conversations.py가 한다."""
import asyncio
from typing import AsyncIterator

from app import budget
from app.config import env, is_fake, num

# 계약서 v1.1 예시 값 (시연 모드 표: 도구 2개 taxonomy·code, 제안 improvement 1 + funnel_design 1)
FAKE_TOOLS = [
    ("taxonomy", "search_taxonomy", {"query": "cart"}, "일치 이벤트 2개: cart_add, cart_view"),
    ("code", "find_event_calls", {"eventName": "scan_complete"}, "2곳: src/app/scan.tsx:405 (실패), src/app/scan.tsx:427 (성공)"),
]
FAKE_CONTENT = ("지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다. "
                "실패의 62%가 OCR 실패이고, 실패 화면에 재시도 동작이 없습니다. 아래 두 제안을 확인해 주세요.")
FAKE_PROPOSALS = [
    {"type": "improvement", "title": "OCR 실패 화면에 재시도·직접 입력 동선 추가",
     "evidence": [{"kind": "metric", "summary": "실패한 scan_complete 중 fail_reason=ocr_empty가 62%다.", "value": "62%",
                   "source": "Amplitude segmentation: scan_complete(success=false) by fail_reason, 2026-09-15~2026-10-14"}],
     "proposal": "OCR 실패 화면에 '다시 찍기'와 '메뉴 이름 직접 입력' 버튼을 둔다.",
     "steps": ["src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.", "직접 입력은 기존 search 화면으로 이동시킨다."],
     "measurement": {"primaryMetric": "scan_start 대비 scan_complete(success=true) 전환율", "baseline": "41.3%",
                     "target": "48%", "funnel": []}},
    {"type": "funnel_design", "title": "스캔 실패 후 재시도 퍼널 측정 설계",
     "evidence": [
         {"kind": "metric", "summary": "최근 30일 scan_start 대비 성공한 scan_complete 전환율이 41.3%다.", "value": "41.3%",
          "source": "Amplitude funnel: scan_start → scan_complete(success=true), 2026-09-15~2026-10-14"},
         {"kind": "code", "summary": "실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다.",
          "file": "src/app/scan.tsx", "function": "onScanFailed", "line": 405,
          "snippet": "track(EVENTS.scan_complete, { success: false, fail_reason: reason, item_count: 0, degraded: false });"},
         {"kind": "taxonomy", "summary": "scan_complete는 성공·실패를 success 속성으로 구분한다.", "eventName": "scan_complete"}],
     "proposal": "실패 화면의 재시도 동작에 신규 이벤트 scan_retry_tap을 심어, 실패 후 재시도로 회복되는 비율을 측정한다.",
     "steps": ["EVENTS 상수에 scan_retry_tap을 추가한다.",
               "src/app/scan.tsx의 handleRetry 첫 줄에서 track(EVENTS.scan_retry_tap, { fail_reason })를 호출한다.",
               "택사노미 문서에 scan_retry_tap 정의와 fail_reason 속성을 추가한다.",
               "배포 후 7일간 아래 퍼널을 Amplitude에 저장해 확인한다."],
     "measurement": {
         "primaryMetric": "scan_complete(success=false) 이후 24시간 내 scan_complete(success=true) 도달 비율",
         "baseline": None, "target": "35%",
         "funnel": [
             {"order": 1, "eventName": "scan_complete", "status": "existing", "condition": "success=false", "location": None, "properties": []},
             {"order": 2, "eventName": "scan_retry_tap", "status": "new", "condition": None,
              "location": {"file": "src/app/scan.tsx", "function": "handleRetry", "line": 398},
              "properties": [{"name": "fail_reason", "type": "string"}]},
             {"order": 3, "eventName": "scan_complete", "status": "existing", "condition": "success=true", "location": None, "properties": []}]}},
]


def agent_model() -> str:
    return env("AGENT_MODEL") or "fake"


async def _fake(message_id: int) -> AsyncIterator[dict]:
    delay = num("FAKE_DELAY_SECONDS", 0.5)
    for i, (source, name, args, summary) in enumerate(FAKE_TOOLS):
        await asyncio.sleep(delay)
        yield {"type": "tool_call", "key": str(i), "source": source, "name": name, "input": args}
        await asyncio.sleep(delay)
        yield {"type": "tool_result", "key": str(i), "status": "succeeded", "summary": summary, "text": summary}
    await asyncio.sleep(delay)
    budget.record("agent", agent_model(), 0, 0, message_id)
    yield {"type": "final", "content": FAKE_CONTENT, "proposals": FAKE_PROPOSALS}


async def run_agent(message_id: int, conversation_id: int, content: str) -> AsyncIterator[dict]:
    if is_fake():
        async for ev in _fake(message_id):
            yield ev
        return
    yield {"type": "error", "code": "UPSTREAM_ERROR", "message": "실제 에이전트 모드는 아직 구현되지 않았습니다."}  # B6
