"""
ENV Vault - 인증 라우터
POST /api/auth/setup    최초 설정 (관리자 생성 + Vault 초기화)
POST /api/auth/login    로그인 (JWT 발급 + Vault 잠금 해제)
POST /api/auth/logout   로그아웃 (토큰 폐기 + Vault 잠금)
POST /api/auth/refresh  액세스 토큰 갱신
GET  /api/auth/status   Vault 상태 확인
POST /api/auth/change-password         로그인 패스워드 변경
POST /api/auth/change-master-password  마스터 패스워드 변경 (재암호화)
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from auth import (
    authenticate_user, create_access_token, create_refresh_token,
    decode_and_validate_token, hash_password, revoke_token, verify_password,
)
from crypto import (
    change_master_password, initialize_vault,
    is_vault_initialized, unlock_vault,
)
from database import get_db
from dependencies import get_current_user
from i18n import AppError, get_translator
from models import ApiKey, ApiKeyHistory, EnvEntry, EnvFileSnapshot, User
from schemas import (
    ChangeMasterPasswordRequest, ChangePasswordRequest,
    LoginRequest, MessageResponse, SetupRequest,
    TokenResponse, VaultStatusResponse,
)
from vault_state import vault
from config import settings
from ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["인증"])
security = HTTPBearer(auto_error=False)


# ──────────────────────────────────────────────────────────────
# 최초 설정
# ──────────────────────────────────────────────────────────────

@router.post(
    "/setup",
    response_model=MessageResponse,
    summary="최초 설정 (최초 1회만 허용)",
)
@limiter.limit("5/minute")
async def setup(
    request: Request,
    req: SetupRequest,
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    """
    - 사용자 계정이 0개인 경우에만 허용
    - Vault salt 생성 + 검증 토큰 저장
    - 관리자 계정 생성
    """
    if db.query(User).count() > 0:
        raise AppError("err.setup_done", 400)

    # Vault 초기화 (AppError 는 전역 핸들러가 번역)
    vault_key = initialize_vault(req.master_password)
    vault.unlock(vault_key)

    # 사용자 생성
    user = User(username=req.username, hashed_password=hash_password(req.password))
    db.add(user)
    db.commit()

    return MessageResponse(message=t("msg.setup_done", username=req.username))


# ──────────────────────────────────────────────────────────────
# 로그인
# ──────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="로그인")
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    # 1. 로그인 인증 (bcrypt) — 실패 시 AppError(401)
    user = authenticate_user(db, req.username, req.password)

    # 2. Vault 잠금 해제 (PBKDF2 + AES 검증) — 실패 시 AppError(401)
    vault_key = unlock_vault(req.master_password)
    vault.unlock(vault_key)

    # 3. 토큰 발급
    access_token = create_access_token(user.username)
    refresh_token, _ = create_refresh_token(user.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ──────────────────────────────────────────────────────────────
# 로그아웃
# ──────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse, summary="로그아웃")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    if credentials:
        try:
            payload = decode_and_validate_token(credentials.credentials, db)
            revoke_token(payload["jti"], db)
        except AppError:
            pass  # 이미 만료/폐기된 토큰도 로그아웃 허용

    vault.lock()
    return MessageResponse(message=t("msg.logout_done"))


# ──────────────────────────────────────────────────────────────
# 토큰 갱신
# ──────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse, summary="액세스 토큰 갱신")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise AppError("err.refresh_required", 401)

    # 검증 실패 시 AppError(401) 가 전역 핸들러로 전파
    payload = decode_and_validate_token(
        credentials.credentials, db, expected_type="refresh"
    )

    # 기존 refresh 토큰 폐기 (재사용 방지)
    revoke_token(payload["jti"], db)

    username = payload["sub"]
    new_access = create_access_token(username)
    new_refresh, _ = create_refresh_token(username)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ──────────────────────────────────────────────────────────────
# 상태 확인
# ──────────────────────────────────────────────────────────────

@router.get("/status", response_model=VaultStatusResponse, summary="Vault 상태")
async def vault_status():
    status_info = vault.status()
    return VaultStatusResponse(
        initialized=is_vault_initialized(),
        vault_unlocked=status_info["unlocked"],
        unlocked_at=status_info["unlocked_at"],
        idle_seconds=status_info["idle_seconds"],
        timeout_minutes=status_info["timeout_minutes"],
    )


# ──────────────────────────────────────────────────────────────
# 패스워드 변경
# ──────────────────────────────────────────────────────────────

@router.post("/change-password", response_model=MessageResponse, summary="로그인 패스워드 변경")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise AppError("err.current_pw_wrong", 400)

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()
    return MessageResponse(message=t("msg.pw_changed"))


@router.post("/change-master-password", response_model=MessageResponse,
             summary="마스터 패스워드 변경 (전체 재암호화)")
async def change_master_pw(
    req: ChangeMasterPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    """
    마스터 패스워드 변경 시:
    1) DB의 모든 암호화값을 수집 (키/엔트리 + 이력 + 스냅샷)
    2) 구 키로 복호화 → 새 키로 재암호화
    3) DB 업데이트 + 새 salt/verify 저장

    주의: 이력(ApiKeyHistory)·스냅샷(EnvFileSnapshot)도 함께 재암호화하지
          않으면 마스터 PW 변경 후 롤백/복원이 복호화 불가가 된다.
    """
    # 모든 암호화값 수집 (순서를 그대로 유지해 재배치)
    api_keys    = db.query(ApiKey).all()
    env_entries = db.query(EnvEntry).all()
    histories   = db.query(ApiKeyHistory).all()
    snapshots   = db.query(EnvFileSnapshot).all()

    all_encrypted = (
        [ak.encrypted_value for ak in api_keys] +
        [ee.encrypted_value for ee in env_entries] +
        [h.encrypted_value for h in histories] +
        [s.encrypted_snapshot for s in snapshots]
    )

    # 구 마스터 PW 불일치 시 unlock_vault 가 AppError(401) 전파
    new_vault_key, re_encrypted = change_master_password(
        req.current_master_password,
        req.new_master_password,
        all_encrypted,
    )

    # DB 업데이트 (수집 순서와 동일하게 분배)
    i = 0
    for ak in api_keys:
        ak.encrypted_value = re_encrypted[i]; i += 1
    for ee in env_entries:
        ee.encrypted_value = re_encrypted[i]; i += 1
    for h in histories:
        h.encrypted_value = re_encrypted[i]; i += 1
    for s in snapshots:
        s.encrypted_snapshot = re_encrypted[i]; i += 1
    db.commit()

    vault.unlock(new_vault_key)
    return MessageResponse(message=t("msg.master_changed"))
