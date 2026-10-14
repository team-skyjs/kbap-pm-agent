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


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    return 0.0  # B5에서 단가표로 채운다


def record(purpose: str, model: str, input_tokens: int, output_tokens: int, message_id: int | None) -> float:
    """모든 모델 호출 뒤 부른다. fake 모드는 0원으로 기록한다(행 수로 호출 횟수를 검사하기 위함)."""
    c = 0.0 if is_fake() else cost(model, input_tokens, output_tokens)
    db.x("INSERT INTO llm_usage (message_id, purpose, model, input_tokens, output_tokens, cost_usd) VALUES (%s,%s,%s,%s,%s,%s)",
         (message_id, purpose, model, input_tokens, output_tokens, c))
    return c
