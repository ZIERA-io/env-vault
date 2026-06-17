"""
ENV Vault - 설정 중앙 관리
모든 상수 및 경로를 한 곳에서 관리
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings:
    # ── 앱 기본 ──────────────────────────────────────────
    APP_NAME: str = "ENV Vault"
    VERSION: str = "1.0.0"

    # ── 서버 (127.0.0.1 전용 - 외부 접근 차단) ──────────
    HOST: str = "127.0.0.1"
    PORT: int = 8443

    # ── JWT ──────────────────────────────────────────────
    # 환경변수로 주입 가능, 없으면 부팅마다 랜덤 생성
    # (재시작 시 기존 토큰 무효화 → 보안 강화)
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15    # 짧은 만료 = 탈취 피해 최소화
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 로그인 보안 ──────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5              # 초과 시 계정 잠금
    LOCKOUT_MINUTES: int = 30
    SESSION_TIMEOUT_MINUTES: int = 60        # 비활성 자동 잠금

    # ── 파일 경로 ─────────────────────────────────────────
    # DATA_DIR 은 ENV_VAULT_DATA_DIR 로 오버라이드 가능 (테스트 격리용)
    DATA_DIR:          Path = Path(os.environ.get("ENV_VAULT_DATA_DIR", str(BASE_DIR / "data")))
    DB_PATH:           Path = DATA_DIR / "vault.db"
    VAULT_SALT_PATH:   Path = DATA_DIR / ".vault_salt"   # PBKDF2 salt
    VAULT_VERIFY_PATH: Path = DATA_DIR / ".vault_verify" # 마스터 PW 검증용
    SSL_CERT_PATH:     Path = BASE_DIR / "certs" / "cert.pem"
    SSL_KEY_PATH:      Path = BASE_DIR / "certs" / "key.pem"

    # ── CORS (로컬 출처만 허용) ───────────────────────────
    ALLOWED_ORIGINS: list = [
        "https://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:8443",
        "https://localhost:8443",
    ]


settings = Settings()
