"""alembic env.py — 운영 DATABASE_URL(비밀번호 URL 인코딩, % 포함)로도 설정을 읽는다.

10/12 운영 첫 마이그레이션이 configparser 보간(%) 오류로 멈추며 URL 전체(비밀번호 포함)를 로그에 찍었다.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_비밀번호에_퍼센트_인코딩이_있어도_alembic이_URL을_읽는다():
    # 닿지 않는 주소 — 보간 단계를 지나 접속 단계까지 가는지만 본다
    env = {**os.environ, "DATABASE_URL": "postgresql+psycopg://u:p%40ss%25w@127.0.0.1:1/x"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "current"], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60
    )
    assert "interpolation" not in result.stderr
    assert "p%40ss" not in result.stderr  # 실패해도 비밀번호가 찍히지 않는다
