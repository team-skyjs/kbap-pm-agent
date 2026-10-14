"""환경변수. 요청마다 읽어 검사 스크립트의 os.environ 변경 반영. 모델명 기본값은 코드에 두지 않음(모델 교체를 설정만으로)."""
import os


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def is_fake() -> bool:
    return env("AGENT_MODE", "fake") != "real"


def num(name: str, default: float) -> float:
    return float(env(name) or default)
