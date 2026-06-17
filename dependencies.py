"""
ENV Vault - FastAPI 의존성
모든 보호된 라우터에서 공통으로 사용
"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from auth import decode_and_validate_token
from database import get_db
from i18n import AppError
from models import User
from vault_state import vault

security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Authorization: Bearer <access_token> 헤더에서 사용자 추출
    유효하지 않으면 401 (AppError → 전역 핸들러가 번역)
    """
    payload = decode_and_validate_token(credentials.credentials, db, expected_type="access")

    user = db.query(User).filter(User.username == payload["sub"]).first()
    if not user or not user.is_active:
        raise AppError("err.user_not_found", 401)

    return user


def get_vault_key(
    _: User = Depends(get_current_user),
) -> bytes:
    """
    인증된 사용자 전제 하에 Vault 키 반환
    Vault가 잠겨 있으면 423 Locked
    """
    if not vault.is_unlocked:
        raise AppError("err.vault_locked", 423)
    return vault.get_key()
