"""LLM 사용량 기록과 예산 상한 (원칙 IV, ADR-9). llm_usage가 비용 집계의 단일 출처."""
import json

from app import db
from app.config import env, is_fake, num
from app.errors import ApiError


def spent() -> float:
    return float(db.one("SELECT COALESCE(SUM(cost_usd), 0) AS s FROM llm_usage")["s"])


def check() -> None:
    if spent() >= num("LLM_BUDGET_USD", 200):
        raise ApiError(403, "BUDGET_EXCEEDED", f"LLM 누적 비용이 예산 {num('LLM_BUDGET_USD', 200):g}달러에 도달해 실행할 수 없습니다.")


# USD / 1M 토큰 (입력, 출력). 모델 문자열에 키가 들어 있으면 적용. LLM_PRICES(JSON)로 덮어쓰거나 추가한다.
# 출처: Anthropic 모델 표(2026-10-06 캐시). 모르는 모델은 가장 비싼 단가로 잡아 예산을 보수적으로 깎는다
PRICES = {"claude-fable-5-1": (10.0, 50.0), "claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0),
          "claude-haiku-5-5": (0.10, 0.50)}
UNKNOWN = (10.0, 50.0)


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    table = {**PRICES, **{k: tuple(v) for k, v in json.loads(env("LLM_PRICES") or "{}").items()}}
    pin, pout = next((v for k, v in sorted(table.items(), key=lambda kv: -len(kv[0])) if k in model), UNKNOWN)
    return round((input_tokens * pin + output_tokens * pout) / 1_000_000, 4)


def record(purpose: str, model: str, input_tokens: int, output_tokens: int, message_id: int | None) -> float:
    """모든 모델 호출 뒤 부른다. fake 모드는 0원으로 기록한다(행 수로 호출 횟수를 검사하기 위함)."""
    c = 0.0 if is_fake() else cost(model, input_tokens, output_tokens)
    db.x("INSERT INTO llm_usage (message_id, purpose, model, input_tokens, output_tokens, cost_usd) VALUES (%s,%s,%s,%s,%s,%s)",
         (message_id, purpose, model, input_tokens, output_tokens, c))
    return c
