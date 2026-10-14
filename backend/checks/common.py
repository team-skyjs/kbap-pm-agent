"""검사 공용 준비: 개발 DB를 건드리지 않도록 `<db>_check` DB를 만들고 비운 뒤 인프로세스 TestClient를 준다.
실행: docker compose exec backend uv run python checks/check_bN.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

url = os.environ.get("DATABASE_URL", "mysql://root:root@127.0.0.1:3307/kbap_pm_agent")
if not url.endswith("_check"):
    os.environ["DATABASE_URL"] = url + "_check"
os.environ.setdefault("AGENT_MODE", "fake")
os.environ["FAKE_DELAY_SECONDS"] = "0"
os.environ["ACCESS_TOKEN"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402


def client() -> TestClient:
    db.init()
    for t in ["llm_usage", "tool_calls", "proposals", "messages", "conversations", "app_settings"]:
        db.x(f"DELETE FROM {t}")
    return TestClient(app)


def ok(name: str):
    print(f"PASS {name}")
