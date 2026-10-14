"""질문 다듬기 모델 비교(실제 키 필요, 비용 발생): 고정 샘플 10건을 두 모델로 순차 다듬어
_workspace/06_refine_model_comparison.md(채점 칸 포함)와 .json(원문)에 기록. 사용량은 llm_usage에 refine으로 남음.
실행: 개발 PC 레포 안 backend/에서 `uv run python checks/compare_refine.py` (compose의 MySQL이 3307에 떠 있어야 함)
키는 환경변수 또는 레포 루트 .env의 *_API_KEY만 읽음(.env의 DATABASE_URL은 컨테이너용이라 무시)."""
import asyncio
import json
import os
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["AGENT_MODE"] = "real"  # 비용을 실제 단가로 기록

MODELS = ["anthropic:claude-haiku-5-5", "anthropic:claude-sonnet-5-5"]
# 택사노미가 DB에 없을 때 쓰는 고정 이름 목록(분석 대상 앱의 실제 이벤트 이름 일부)
FALLBACK_NAMES = ["scan_start", "scan_complete", "scan_item_add", "scan_permission", "order_card_open",
                  "order_share_view", "review_write_tap", "review_translate_toggle", "food_bookmark_toggle",
                  "push_consent_response", "push_permission", "push_pref_toggle", "auth_login_success",
                  "auth_gate_view", "app_tab_view", "community_comment_submit", "error_state_view"]
# (유형, 질문, 직전 대화). 유형 구성: 일상어 이탈 2, 기간 없는 지표 2, 측정 설계 2, 후속 2, 이미 구체적 1, 목록 밖 대상 1
SAMPLES = [
    ("일상어 이탈", "요즘 스캔하다가 사람들이 많이 나가는 것 같은데 왜 그래?", []),
    ("일상어 이탈", "주문까지 안 가고 중간에 그만두는 사람 많아?", []),
    ("기간 없는 지표", "스캔 성공률 알려줘", []),
    ("기간 없는 지표", "리뷰 쓰는 사람 비율 어때?", []),
    ("측정 설계", "장바구니 개선 효과를 보려면 뭘 재야 해?", []),
    ("측정 설계", "스캔 실패 화면에 재시도 버튼 넣으면 효과를 어떻게 측정해?", []),
    ("후속", "그걸 주 단위로 쪼개서 보여줘",
     [{"role": "user", "content": "지난 30일 scan_start → scan_complete(success=true) 전환율 알려줘"},
      {"role": "assistant", "content": "지난 30일 scan_start 2,418명 중 scan_complete(success=true) 999명으로 전환율은 41.3%입니다."}]),
    ("후속", "제일 낮은 데는 왜 그래?",
     [{"role": "user", "content": "국가별 스캔 완료율 비교해줘"},
      {"role": "assistant", "content": "최근 30일 스캔 완료율은 KR 41.3%, JP 38.0%, US 45.2%입니다."}]),
    ("이미 구체적", "최근 14일 scan_start 대비 scan_complete(success=true) 전환율을 일별로 보여주고, 가장 낮은 날의 실패 사유 분포도 같이 줘.", []),
    ("목록 밖 대상", "결제 화면에서 이탈하는 사람 얼마나 돼?", []),
]
CRITERIA = ["의도 보존", "실제 이벤트 이름", "기간·지표 명시", "자연스러움"]


def load_keys() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip().endswith("_API_KEY") and v.strip() and not os.environ.get(k.strip()):
            os.environ[k.strip()] = v.strip()


async def run_one(model: str, prompt: str) -> dict:
    from app import agent, budget
    mod, name = agent.runtime(model)
    t0 = time.monotonic()
    try:
        result, i, o = await mod.refine(name, prompt)
    except Exception as e:
        return {"model": model, "error": f"{type(e).__name__}: {str(e)[:200]}", "latency_s": round(time.monotonic() - t0, 2)}
    latency = round(time.monotonic() - t0, 2)
    try:
        cost = budget.record("refine", model, i, o, None)
    except Exception:  # DB가 없어도 비교는 계속, 비용은 단가표로 계산해 표에 기록
        cost = budget.cost(model, i, o)
    return {"model": model, "refined": result.refined, "summary": result.summary, "latency_s": latency,
            "input_tokens": i, "output_tokens": o, "cost_usd": cost}


def sentences(text: str) -> str:
    """두 문장 이내 규칙 확인용(경고만). 한국어 문장 분리가 불안정해 마침표·물음표 기준 근사"""
    n = len([x for x in re.split(r"[.?!。]\s*", text) if x.strip()])
    return f"{n} ⚠" if n > 2 else str(n)


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_md(rows: list[dict], names_source: str) -> str:
    out = ["# 질문 다듬기 모델 비교", "",
           f"모델: {', '.join(MODELS)}. 택사노미 이름 출처: {names_source}. 채점(각 0~2점): {', '.join(CRITERIA)}.",
           "결정 규칙: Sonnet 합계가 Haiku보다 8점 이상 높거나 Haiku 의도 보존 0점이 2건 이상이면 Sonnet, 아니면 Haiku.", ""]
    for n, r in enumerate(rows, 1):
        out += [f"## {n}. {r['type']}", "", f"원문: {r['question']}"]
        if r["history"]:
            out.append("직전 대화: " + " / ".join(f"[{h['role']}] {h['content']}" for h in r["history"]))
        out += ["", "| 모델 | 개선안 | 문장 수 | 요약 | 지연(초) | 토큰(입력/출력) | 비용(USD) |", "|---|---|---|---|---|---|---|"]
        for res in r["results"]:
            if "error" in res:
                out.append(f"| {res['model']} | 오류: {cell(res['error'])} | | | {res['latency_s']} | | |")
            else:
                out.append(f"| {res['model']} | {cell(res['refined'])} | {sentences(res['refined'])} | {cell(res['summary'])} | {res['latency_s']} | "
                           f"{res['input_tokens']}/{res['output_tokens']} | {res['cost_usd']} |")
        out += ["", "| 채점 | Haiku | Sonnet |", "|---|---|---|"] + [f"| {c} | | |" for c in CRITERIA] + [""]
    out += ["## 합계", "", "| | Haiku | Sonnet |", "|---|---|---|", "| 합계(80점 만점) | | |",
            "| 의도 보존 0점 건수 | | |", "| 평균 지연(초) | " + " | ".join(
                str(round(sum(x["latency_s"] for r in rows for x in r["results"] if x["model"] == m) / len(rows), 2))
                for m in MODELS) + " |",
            "| 비용 합계(USD) | " + " | ".join(
                str(round(sum(x.get("cost_usd", 0) for r in rows for x in r["results"] if x["model"] == m), 4))
                for m in MODELS) + " |", "", "## 결정", "", "(채점 후 작성)", ""]
    return "\n".join(out)


async def main(out_dir: pathlib.Path = ROOT / "_workspace") -> list[dict]:
    from app import budget, refine
    load_keys()
    try:
        names, source = refine.taxonomy_names(), "DB"
        budget.check()
    except Exception as e:
        if getattr(e, "code", "") == "BUDGET_EXCEEDED":
            raise
        names, source = [], "고정 목록(DB 없음)"
    if not names:
        names, source = FALLBACK_NAMES, source if source != "DB" else "고정 목록(DB에 택사노미 없음)"
    rows = []
    for kind, question, history in SAMPLES:
        prompt = refine.render_prompt(question, refine.cap_names(names, question)[0], history)
        results = [await run_one(m, prompt) for m in MODELS]  # 순차 호출(지연 비교가 서로 간섭하지 않게)
        rows.append({"type": kind, "question": question, "history": history, "results": results})
        print(json.dumps(rows[-1], ensure_ascii=False))
    (out_dir / "06_refine_model_comparison.md").write_text(write_md(rows, source))
    (out_dir / "06_refine_model_comparison.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    return rows


if __name__ == "__main__":
    asyncio.run(main())
