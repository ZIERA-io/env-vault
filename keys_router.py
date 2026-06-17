"""
ENV Vault - API 키 라우터
─────────────────────────────────────────────────────────
GET    /api/keys                       전체 키 목록 (값 제외)
POST   /api/keys                       키 생성 (평문 → 암호화 저장)
GET    /api/keys/export                암호화 백업 파일 생성  ← {id} 보다 먼저 선언
POST   /api/keys/import                암호화 백업 복원
GET    /api/keys/{id}                  키 상세 (값 제외)
GET    /api/keys/{id}/value            복호화된 값 반환
PUT    /api/keys/{id}                  키 수정 (값 변경 시 이력 자동 저장)
DELETE /api/keys/{id}                  키 삭제
GET    /api/keys/{id}/history          변경 이력 목록
POST   /api/keys/{id}/rollback/{hid}   이전 값으로 롤백
─────────────────────────────────────────────────────────
모든 민감 값은 AES-256-GCM 암호화 상태로만 DB 저장.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

import crypto
from database import get_db
from dependencies import get_current_user, get_vault_key
from i18n import AppError, get_translator
from models import ApiKey, ApiKeyHistory, User
from schemas import (
    ApiKeyCreate, ApiKeyExportRequest, ApiKeyHistoryItem,
    ApiKeyImportRequest, ApiKeyImportResult, ApiKeyResponse,
    ApiKeyUpdate, ApiKeyWithValue, MessageResponse,
)

router = APIRouter(prefix="/keys", tags=["API 키"])

_BACKUP_VERSION = "env-vault-backup/1"


def _get_key_or_404(db: Session, key_id: int) -> ApiKey:
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise AppError("err.key_not_found", 404)
    return key


# ──────────────────────────────────────────────────────────────
# 목록 / 생성
# ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[ApiKeyResponse], summary="API 키 목록 (값 제외)")
async def list_keys(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.post("", response_model=ApiKeyResponse, status_code=201, summary="API 키 생성")
async def create_key(
    req: ApiKeyCreate,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    key = ApiKey(
        name=req.name,
        service=req.service,
        encrypted_value=crypto.encrypt(req.value, vault_key),
        description=req.description,
        tags=req.tags,
        expires_at=req.expires_at,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


# ──────────────────────────────────────────────────────────────
# 백업 export / import  (정적 경로 — {id} 라우트보다 먼저 선언)
# ──────────────────────────────────────────────────────────────

@router.post("/export", response_class=PlainTextResponse, summary="암호화 백업 생성")
async def export_keys(
    req: ApiKeyExportRequest,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    """
    전체 키를 평문으로 복원한 뒤, 백업 전용 패스워드로 재암호화한
    자가완결(.envbackup) 파일을 반환한다. 마스터 PW와 독립적이라
    다른 환경에서도 복원 가능.
    """
    keys = db.query(ApiKey).all()
    payload = {
        "version": _BACKUP_VERSION,
        "exported_at": datetime.utcnow().isoformat(),
        "keys": [
            {
                "name": k.name,
                "service": k.service,
                "value": crypto.decrypt(k.encrypted_value, vault_key),
                "description": k.description,
                "tags": k.tags,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            }
            for k in keys
        ],
    }
    blob = crypto.encrypt_with_password(json.dumps(payload, ensure_ascii=False), req.backup_password)
    return PlainTextResponse(
        content=blob,
        headers={"Content-Disposition": 'attachment; filename="keys.envbackup"'},
    )


@router.post("/import", response_model=ApiKeyImportResult, summary="암호화 백업 복원")
async def import_keys(
    req: ApiKeyImportRequest,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    try:
        decoded = crypto.decrypt_with_password(req.content.strip(), req.backup_password)
        payload = json.loads(decoded)
    except ValueError:
        raise AppError("err.backup_decrypt_failed", 400)
    except json.JSONDecodeError:
        raise AppError("err.backup_format", 400)

    if not isinstance(payload, dict) or payload.get("version") != _BACKUP_VERSION:
        raise AppError("err.backup_version", 400)

    imported = skipped = 0
    for item in payload.get("keys", []):
        name, service = item.get("name"), item.get("service")
        value = item.get("value")
        if not name or not service or value is None:
            skipped += 1
            continue

        existing = (
            db.query(ApiKey)
            .filter(ApiKey.name == name, ApiKey.service == service)
            .first()
        )
        expires_at = item.get("expires_at")
        expires_dt = datetime.fromisoformat(expires_at) if expires_at else None

        if existing:
            if not req.overwrite:
                skipped += 1
                continue
            # 덮어쓰기: 기존 값 이력 보존 후 갱신
            db.add(ApiKeyHistory(
                api_key_id=existing.id,
                encrypted_value=existing.encrypted_value,
                note="import 덮어쓰기 전 백업",
            ))
            existing.encrypted_value = crypto.encrypt(value, vault_key)
            existing.description = item.get("description")
            existing.tags = item.get("tags")
            existing.expires_at = expires_dt
        else:
            db.add(ApiKey(
                name=name,
                service=service,
                encrypted_value=crypto.encrypt(value, vault_key),
                description=item.get("description"),
                tags=item.get("tags"),
                expires_at=expires_dt,
            ))
        imported += 1

    db.commit()
    return ApiKeyImportResult(
        imported=imported,
        skipped=skipped,
        message=t("msg.import_done", imported=imported, skipped=skipped),
    )


# ──────────────────────────────────────────────────────────────
# 상세 / 값 / 수정 / 삭제
# ──────────────────────────────────────────────────────────────

@router.get("/{key_id}", response_model=ApiKeyResponse, summary="키 상세 (값 제외)")
async def get_key(
    key_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_key_or_404(db, key_id)


@router.get("/{key_id}/value", response_model=ApiKeyWithValue, summary="복호화된 값 반환")
async def get_key_value(
    key_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    key = _get_key_or_404(db, key_id)
    try:
        value = crypto.decrypt(key.encrypted_value, vault_key)
    except ValueError:
        raise AppError("err.decrypt_failed", 500)
    data = ApiKeyResponse.model_validate(key).model_dump()
    data["value"] = value
    return ApiKeyWithValue(**data)


@router.put("/{key_id}", response_model=ApiKeyResponse, summary="키 수정 (값 변경 시 이력 저장)")
async def update_key(
    key_id: int,
    req: ApiKeyUpdate,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    key = _get_key_or_404(db, key_id)

    # 값이 새로 들어오면: 기존 암호화값을 이력에 먼저 저장 후 갱신
    if req.value is not None:
        db.add(ApiKeyHistory(
            api_key_id=key.id,
            encrypted_value=key.encrypted_value,
            note="값 수정 전 자동 백업",
        ))
        key.encrypted_value = crypto.encrypt(req.value, vault_key)

    for field in ("name", "service", "description", "tags", "expires_at", "is_active"):
        new_val = getattr(req, field)
        if new_val is not None:
            setattr(key, field, new_val)

    db.commit()
    db.refresh(key)
    return key


@router.delete("/{key_id}", response_model=MessageResponse, summary="키 삭제")
async def delete_key(
    key_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    key = _get_key_or_404(db, key_id)
    name = key.name
    db.delete(key)        # 이력은 cascade 로 함께 삭제
    db.commit()
    return MessageResponse(message=t("msg.key_deleted", name=name))


# ──────────────────────────────────────────────────────────────
# 이력 / 롤백
# ──────────────────────────────────────────────────────────────

@router.get("/{key_id}/history", response_model=list[ApiKeyHistoryItem], summary="변경 이력 목록")
async def list_history(
    key_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_key_or_404(db, key_id)
    return (
        db.query(ApiKeyHistory)
        .filter(ApiKeyHistory.api_key_id == key_id)
        .order_by(ApiKeyHistory.changed_at.desc())
        .all()
    )


@router.post("/{key_id}/rollback/{history_id}", response_model=ApiKeyResponse, summary="이전 값으로 롤백")
async def rollback_key(
    key_id: int,
    history_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    key = _get_key_or_404(db, key_id)
    hist = (
        db.query(ApiKeyHistory)
        .filter(ApiKeyHistory.id == history_id, ApiKeyHistory.api_key_id == key_id)
        .first()
    )
    if not hist:
        raise AppError("err.history_not_found", 404)

    # 롤백 대상 값이 현재 Vault 키로 복호화 가능한지 검증
    try:
        crypto.decrypt(hist.encrypted_value, vault_key)
    except ValueError:
        raise AppError("err.rollback_failed", 400)

    # 현재 값을 이력에 보존한 뒤 과거 값으로 되돌림
    db.add(ApiKeyHistory(
        api_key_id=key.id,
        encrypted_value=key.encrypted_value,
        note=f"롤백 전 값 (history #{history_id} 로 복원)",
    ))
    key.encrypted_value = hist.encrypted_value
    db.commit()
    db.refresh(key)
    return key
