"""시스템 프롬프트 검사: 시계열 답변의 chart 블록 지시 문장과 형식 예시가 형식 기준 문서와 글자 단위로 같은지.
기준은 specs/003-frontend-redesign/contracts/chart-block.md의 선 예시(첫 chart 블록). 레포 안에서 실행(문서가 이미지에 없음).
실행: backend/에서 uv run python checks/check_b9.py"""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import SYSTEM_PROMPT  # noqa: E402

SENTENCE = "시계열 지표(날짜별 수치)를 답할 때는 본문에 chart 코드 블록을 함께 쓴다. 형식:"
doc = next((d / "specs/003-frontend-redesign/contracts/chart-block.md" for d in pathlib.Path(__file__).resolve().parents
            if (d / "specs/003-frontend-redesign/contracts/chart-block.md").is_file()), None)
assert doc, "chart-block.md를 찾지 못함: 레포 안에서 실행할 것"
lines = doc.read_text().splitlines()
example = lines[lines.index("```chart") + 1]  # 첫 chart 블록 = 선 예시
assert example.startswith('{"type":"line"'), f"첫 chart 블록이 선 예시가 아님: {example[:40]}"

assert SENTENCE in SYSTEM_PROMPT, "chart 블록 지시 문장 없음"
print("PASS 지시 문장 글자 단위 일치")
assert f"{SENTENCE}\n```chart\n{example}\n```" in SYSTEM_PROMPT, "형식 예시가 기준 문서의 선 예시와 다름"
print("PASS 선 예시 JSON 글자 단위 일치(chart 펜스 포함)")
print("check_b9 OK")
