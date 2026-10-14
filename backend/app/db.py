"""MySQL 접근. ponytail: ORM·커넥션 풀 없이 pymysql 쿼리마다 연결. 동시 사용자 늘면 풀(DBUtils) 또는 SQLAlchemy Core로"""
import json
import pathlib
from datetime import datetime
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor

from app.config import env

SCHEMA = pathlib.Path(__file__).resolve().parent.parent / "schema.sql"


def _params() -> dict:
    u = urlparse(env("DATABASE_URL", "mysql://root:root@127.0.0.1:3307/kbap_pm_agent"))
    return {"host": u.hostname, "port": u.port or 3306, "user": unquote(u.username or ""),
            "password": unquote(u.password or ""), "database": u.path.lstrip("/")}


def connect(with_db: bool = True):
    p = _params()
    name = p.pop("database")
    return pymysql.connect(**p, database=name if with_db else None, charset="utf8mb4", autocommit=True,
                           cursorclass=DictCursor, connect_timeout=5, init_command="SET time_zone='+00:00'")


def init() -> None:
    name = _params()["database"]
    try:  # 전용 계정은 CREATE DATABASE 권한이 없을 수 있다. 이미 있으면 그대로 진행
        with connect(False) as c, c.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except pymysql.MySQLError:
        pass
    sql = "\n".join(l for l in SCHEMA.read_text().splitlines() if not l.strip().startswith("--"))
    with connect() as c, c.cursor() as cur:
        for stmt in sql.split(";"):
            if stmt.strip():
                cur.execute(stmt)


def q(sql: str, args=()) -> list[dict]:
    with connect() as c, c.cursor() as cur:
        cur.execute(sql, args)
        return list(cur.fetchall())


def one(sql: str, args=()) -> dict | None:
    rows = q(sql, args)
    return rows[0] if rows else None


def x(sql: str, args=()) -> int:
    """INSERT/UPDATE 실행. lastrowid 반환."""
    with connect() as c, c.cursor() as cur:
        cur.execute(sql, args)
        return cur.lastrowid


def iso(dt: datetime | None) -> str | None:
    return None if dt is None else dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def now_iso() -> str:
    from datetime import timezone
    return iso(datetime.now(timezone.utc))


def get_setting(k: str):
    row = one("SELECT v FROM app_settings WHERE k=%s", (k,))
    return None if row is None else json.loads(row["v"])


def set_setting(k: str, v) -> None:
    x("INSERT INTO app_settings (k, v) VALUES (%s, %s) ON DUPLICATE KEY UPDATE v=VALUES(v)",
      (k, json.dumps(v, ensure_ascii=False)))


def del_setting(k: str) -> None:
    x("DELETE FROM app_settings WHERE k=%s", (k,))
