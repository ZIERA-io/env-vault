"""
ENV Vault - 인증 모듈
─────────────────────────────────────────────────────────
비밀번호: bcrypt (cost factor 12)
세션:     JWT  access(15분) + refresh(7일)
보안:     로그인 5회 실패 → 30분 잠금
         로그아웃된 JTI는 DB 블랙리스트에 영구 저장
─────────────────────────────────────────────────────────
"""

import secrets
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import settings
from i18n import AppError
from models import RevokedToken, User


# ──────────────────────────────────────────────────────────────
# 비밀번호 (bcrypt cost=12, 직접 사용 - passlib 버전 비호환 우회)
# ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """bcrypt 해시 (cost=12 ≈ 300ms, brute-force 저항)"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# 존재하지 않는 계정에서도 동일한 bcrypt 비용을 소모해 사용자 열거(timing) 방지
_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt(rounds=12))


def _burn_password_check() -> None:
    bcrypt.checkpw(b"x", _DUMMY_HASH)


# ──────────────────────────────────────────────────────────────
# JWT
# ──────────────────────────────────────────────────────────────

def _create_token(data: dict, expires_delta: timedelta) -> tuple[str, str]:
    """JWT 생성 → (token_string, jti) 반환"""
    jti = secrets.token_urlsafe(16)
    payload = {
        **data,
        "jti": jti,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + expires_delta,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_access_token(username: str) -> str:
    token, _ = _create_token(
        {"sub": username, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return token


def create_refresh_token(username: str) -> tuple[str, str]:
    """(refresh_token, jti) 반환"""
    return _create_token(
        {"sub": username, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_and_validate_token(token: str, db: Session, expected_type: str = "access") -> dict:
    """
    JWT 검증:
    1) 서명 / 만료 확인
    2) 블랙리스트(로그아웃) 확인
    3) 토큰 타입 확인
    실패 시 ValueError
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise AppError("err.invalid_token", 401)

    jti = payload.get("jti")
    if db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        raise AppError("err.logged_out_token", 401)

    if payload.get("type") != expected_type:
        raise AppError("err.token_type", 401)

    return payload


def revoke_token(jti: str, db: Session) -> None:
    """JTI를 블랙리스트에 추가 (로그아웃/토큰 갱신 시 호출)"""
    if not db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        db.add(RevokedToken(jti=jti))
        db.commit()


def cleanup_expired_revoked_tokens(db: Session) -> int:
    """
    블랙리스트 위생 관리.
    토큰 최대 수명은 refresh(7일)이므로, 폐기 시점이 7일보다 오래된 JTI 는
    원본 토큰이 이미 만료되어 블랙리스트에 남길 필요가 없다.
    반환: 삭제된 행 수.
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    deleted = (
        db.query(RevokedToken)
        .filter(RevokedToken.revoked_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


# ──────────────────────────────────────────────────────────────
# 로그인
# ──────────────────────────────────────────────────────────────

def authenticate_user(db: Session, username: str, password: str) -> User:
    """
    사용자 인증:
    - 존재하지 않는 계정도 동일 에러 반환 (사용자 열거 방지)
    - 잠금 상태 확인
    - 실패 횟수 초과 시 잠금 설정
    """
    user = db.query(User).filter(User.username == username).first()

    if not user or not user.is_active:
        _burn_password_check()   # 타이밍 평준화 (사용자 열거 방지)
        raise AppError("err.wrong_credentials", 401)

    # 잠금 확인
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
        raise AppError("err.account_locked", 401, minutes=remaining)

    if not verify_password(password, user.hashed_password):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
            user.failed_attempts = 0
            db.commit()
            raise AppError(
                "err.too_many_attempts", 401,
                max=settings.MAX_LOGIN_ATTEMPTS,
                lockout=settings.LOCKOUT_MINUTES,
            )
        db.commit()
        raise AppError("err.wrong_credentials", 401)

    # 성공: 초기화
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()
    return user
