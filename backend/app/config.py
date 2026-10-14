"""환경변수. 요청마다 읽어 검사 스크립트가 os.environ으로 바꿀 수 있게 한다. 모델명 기본값은 코드에 두지 않는다(원칙 III)."""
import os


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def is_fake() -> bool:
    return env("AGENT_MODE", "fake") != "real"


def num(name: str, default: float) -> float:
    return float(env(name) or default)
