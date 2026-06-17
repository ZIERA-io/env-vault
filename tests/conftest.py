"""
pytest 공용 픽스처
─────────────────────────────────────────────────────────
· 데이터 디렉토리를 임시 경로로 격리 (ENV_VAULT_DATA_DIR)
· rate limit 비활성화 (ENV_VAULT_DISABLE_RATELIMIT)
· 테스트마다 DB/Vault 상태 초기화
앱 모듈 import 전에 환경변수를 먼저 설정해야 한다.
"""

import os
import sys
import tempfile
from pathlib import Path

# 앱 import 전에 환경 격리 설정 (config 가 import 시점에 경로를 읽음)
_TMP = tempfile.mkdtemp(prefix="envvault_test_")
os.environ["ENV_VAULT_DATA_DIR"] = _TMP
os.environ["ENV_VAULT_DISABLE_RATELIMIT"] = "1"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

# 프로젝트 루트를 import 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    import main
    from database import Base, engine
    from vault_state import vault
    from config import settings

    # 깨끗한 상태로 초기화
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    for p in (settings.VAULT_SALT_PATH, settings.VAULT_VERIFY_PATH):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    vault.lock()

    with TestClient(main.app, base_url="http://localhost") as c:
        yield c


CREDS = {
    "username": "admin",
    "password": "password123",
    "master_password": "master123456",
}


@pytest.fixture()
def auth(client):
    """setup + login 후 Authorization 헤더 반환"""
    client.post("/api/auth/setup", json=CREDS)
    r = client.post("/api/auth/login", json=CREDS)
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
