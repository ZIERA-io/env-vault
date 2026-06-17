"""
ENV Vault - .env 파일 라우터
─────────────────────────────────────────────────────────
파일 등록/조회/해제, 디스크 동기화(pull/push), 엔트리 CRUD,
스냅샷·복원·diff, 로컬 코드 사용처 스캔.
값은 항상 AES-256-GCM 암호화 상태로만 DB 저장.
─────────────────────────────────────────────────────────
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import crypto
from database import get_db
from dependencies import get_current_user, get_vault_key
from i18n import AppError, get_translator
from envparse import parse_env, serialize_env
from models import ApiKey, EnvEntry, EnvFile, EnvFileSnapshot, User
from schemas import (
    ApiKeyResponse, DiffItem, DiffResponse, EnvEntryCreate, EnvEntryResponse,
    EnvEntryUpdate, EnvEntryWithValue, EnvFileCreate,
    EnvFileDetailResponse, EnvFileResponse, MessageResponse,
    ScanMatch, ScanRequest, ScanResponse, SnapshotResponse, SyncResult,
)

router = APIRouter(prefix="/envfiles", tags=[".env 파일"])

# 스캔 시 건너뛸 디렉토리 / 한도
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
              "dist", "build", ".next", ".idea", ".mypy_cache"}
_SCAN_MAX_FILES = 5000
_SCAN_MAX_MATCHES = 500
_SCAN_MAX_FILE_BYTES = 2_000_000


# ──────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────

def _mask(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}…{value[-4:]}"


def _get_file_or_404(db: Session, file_id: int) -> EnvFile:
    f = db.query(EnvFile).filter(EnvFile.id == file_id).first()
    if not f:
        raise AppError("err.file_not_found", 404)
    return f


def _get_entry_or_404(db: Session, file_id: int, entry_id: int) -> EnvEntry:
    e = (
        db.query(EnvEntry)
        .filter(EnvEntry.id == entry_id, EnvEntry.env_file_id == file_id)
        .first()
    )
    if not e:
        raise AppError("err.entry_not_found", 404)
    return e


def _file_response(f: EnvFile) -> EnvFileResponse:
    return EnvFileResponse(
        id=f.id, name=f.name, file_path=f.file_path,
        project_name=f.project_name, environment=f.environment,
        last_synced_at=f.last_synced_at, created_at=f.created_at,
        entry_count=len(f.entries),
        file_exists=Path(f.file_path).exists(),
    )


def _create_snapshot(db: Session, f: EnvFile, vault_key: bytes, label: Optional[str]) -> EnvFileSnapshot:
    """현재 엔트리 전체를 평문 복원 → JSON → Vault 키로 암호화하여 스냅샷 저장."""
    payload = [
        {
            "key": e.key,
            "value": crypto.decrypt(e.encrypted_value, vault_key),
            "comment": e.comment,
        }
        for e in f.entries
    ]
    snap = EnvFileSnapshot(
        env_file_id=f.id,
        label=label,
        encrypted_snapshot=crypto.encrypt(json.dumps(payload, ensure_ascii=False), vault_key),
    )
    db.add(snap)
    return snap


def _load_snapshot(snap: EnvFileSnapshot, vault_key: bytes) -> list[dict]:
    return json.loads(crypto.decrypt(snap.encrypted_snapshot, vault_key))


# ──────────────────────────────────────────────────────────────
# 파일 목록 / 등록 / 상세 / 해제
# ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[EnvFileResponse], summary=".env 파일 목록")
async def list_files(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files = db.query(EnvFile).order_by(EnvFile.created_at.desc()).all()
    return [_file_response(f) for f in files]


@router.post("", response_model=EnvFileResponse, status_code=201, summary=".env 파일 등록")
async def register_file(
    req: EnvFileCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = EnvFile(
        name=req.name,
        file_path=req.file_path,
        project_name=req.project_name,
        environment=req.environment,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _file_response(f)


@router.get("/{file_id}", response_model=EnvFileDetailResponse, summary="파일 상세 + 엔트리")
async def get_file(
    file_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = _get_file_or_404(db, file_id)
    base = _file_response(f).model_dump()
    base["entries"] = [
        EnvEntryResponse.model_validate(e)
        for e in sorted(f.entries, key=lambda e: e.key)
    ]
    return EnvFileDetailResponse(**base)


@router.delete("/{file_id}", response_model=MessageResponse, summary="파일 등록 해제 (디스크 파일은 유지)")
async def unregister_file(
    file_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    f = _get_file_or_404(db, file_id)
    name = f.name
    db.delete(f)        # entries / snapshots 는 cascade 삭제
    db.commit()
    return MessageResponse(message=t("msg.file_unregistered", name=name))


# ──────────────────────────────────────────────────────────────
# 디스크 동기화
# ──────────────────────────────────────────────────────────────

@router.post("/{file_id}/sync/pull", response_model=SyncResult, summary="디스크 → DB 동기화")
async def sync_pull(
    file_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    f = _get_file_or_404(db, file_id)
    path = Path(f.file_path)
    if not path.exists() or not path.is_file():
        raise AppError("err.file_missing_disk", 400, path=f.file_path)

    parsed = parse_env(path.read_text(encoding="utf-8"))

    # 변경이 생길 수 있으므로 현재 상태를 먼저 스냅샷으로 보존
    if f.entries:
        _create_snapshot(db, f, vault_key, label="pull 자동 백업")

    existing = {e.key: e for e in f.entries}
    added = updated = kept = 0

    for item in parsed:
        key, value, comment = item["key"], item["value"], item["comment"]
        cur = existing.get(key)
        if cur is None:
            db.add(EnvEntry(
                env_file_id=f.id,
                key=key,
                encrypted_value=crypto.encrypt(value, vault_key),
                comment=comment,
            ))
            added += 1
        else:
            old_value = crypto.decrypt(cur.encrypted_value, vault_key)
            if old_value != value or (cur.comment or None) != (comment or None):
                cur.encrypted_value = crypto.encrypt(value, vault_key)
                cur.comment = comment
                updated += 1
            else:
                kept += 1

    # DB 에만 있는 키는 충돌 방지를 위해 유지 (삭제하지 않음)
    parsed_keys = {i["key"] for i in parsed}
    kept += sum(1 for k in existing if k not in parsed_keys)

    f.last_synced_at = datetime.utcnow()
    db.commit()
    return SyncResult(
        direction="pull", added=added, updated=updated, kept=kept,
        message=t("msg.sync_pull", added=added, updated=updated, kept=kept),
    )


@router.post("/{file_id}/sync/push", response_model=SyncResult, summary="DB → 디스크 동기화")
async def sync_push(
    file_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    f = _get_file_or_404(db, file_id)
    path = Path(f.file_path)
    if not path.parent.exists():
        raise AppError("err.parent_missing", 400, path=str(path.parent))

    # 디스크 덮어쓰기 전 현재 DB 상태 스냅샷 보존
    if f.entries:
        _create_snapshot(db, f, vault_key, label="push 자동 백업")

    rows = [
        {
            "key": e.key,
            "value": crypto.decrypt(e.encrypted_value, vault_key),
            "comment": e.comment,
        }
        for e in sorted(f.entries, key=lambda e: e.key)
    ]
    path.write_text(serialize_env(rows), encoding="utf-8")

    f.last_synced_at = datetime.utcnow()
    db.commit()
    return SyncResult(
        direction="push", updated=len(rows),
        message=t("msg.sync_push", count=len(rows), path=f.file_path),
    )


# ──────────────────────────────────────────────────────────────
# 엔트리 CRUD
# ──────────────────────────────────────────────────────────────

@router.get("/{file_id}/entries", response_model=list[EnvEntryResponse], summary="엔트리 목록 (값 제외)")
async def list_entries(
    file_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = _get_file_or_404(db, file_id)
    return sorted(f.entries, key=lambda e: e.key)


@router.get("/{file_id}/entries/{entry_id}/value", response_model=EnvEntryWithValue,
            summary="특정 엔트리 복호화값")
async def get_entry_value(
    file_id: int,
    entry_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    e = _get_entry_or_404(db, file_id, entry_id)
    data = EnvEntryResponse.model_validate(e).model_dump()
    data["value"] = crypto.decrypt(e.encrypted_value, vault_key)
    return EnvEntryWithValue(**data)


@router.post("/{file_id}/entries", response_model=EnvEntryResponse, status_code=201, summary="엔트리 추가")
async def create_entry(
    file_id: int,
    req: EnvEntryCreate,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    f = _get_file_or_404(db, file_id)
    if any(e.key == req.key for e in f.entries):
        raise AppError("err.key_exists", 409, key=req.key)
    e = EnvEntry(
        env_file_id=f.id,
        key=req.key,
        encrypted_value=crypto.encrypt(req.value, vault_key),
        comment=req.comment,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.put("/{file_id}/entries/{entry_id}", response_model=EnvEntryResponse, summary="엔트리 수정")
async def update_entry(
    file_id: int,
    entry_id: int,
    req: EnvEntryUpdate,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    e = _get_entry_or_404(db, file_id, entry_id)
    if req.value is not None:
        e.encrypted_value = crypto.encrypt(req.value, vault_key)
    if req.comment is not None:
        e.comment = req.comment
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{file_id}/entries/{entry_id}", response_model=MessageResponse, summary="엔트리 삭제")
async def delete_entry(
    file_id: int,
    entry_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    e = _get_entry_or_404(db, file_id, entry_id)
    key = e.key
    db.delete(e)
    db.commit()
    return MessageResponse(message=t("msg.entry_deleted", key=key))


# ──────────────────────────────────────────────────────────────
# API 키 ↔ 엔트리 연결 (M:N)
# ──────────────────────────────────────────────────────────────

@router.get("/{file_id}/entries/{entry_id}/links", response_model=list[ApiKeyResponse],
            summary="엔트리에 연결된 API 키 목록")
async def list_entry_links(
    file_id: int,
    entry_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    e = _get_entry_or_404(db, file_id, entry_id)
    return e.linked_api_keys


@router.post("/{file_id}/entries/{entry_id}/links/{key_id}", response_model=MessageResponse,
             summary="엔트리에 API 키 연결")
async def add_entry_link(
    file_id: int,
    entry_id: int,
    key_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    e = _get_entry_or_404(db, file_id, entry_id)
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise AppError("err.key_not_found", 404)
    if key not in e.linked_api_keys:
        e.linked_api_keys.append(key)
        db.commit()
    return MessageResponse(message=t("msg.link_added", key=e.key, name=key.name))


@router.delete("/{file_id}/entries/{entry_id}/links/{key_id}", response_model=MessageResponse,
               summary="엔트리-API 키 연결 해제")
async def remove_entry_link(
    file_id: int,
    entry_id: int,
    key_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    e = _get_entry_or_404(db, file_id, entry_id)
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if key and key in e.linked_api_keys:
        e.linked_api_keys.remove(key)
        db.commit()
    return MessageResponse(message=t("msg.link_removed"))


# ──────────────────────────────────────────────────────────────
# 스냅샷 / 복원 / diff
# ──────────────────────────────────────────────────────────────

@router.post("/{file_id}/snapshot", response_model=SnapshotResponse, status_code=201, summary="스냅샷 저장")
async def create_snapshot(
    file_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    label: Optional[str] = None,
):
    f = _get_file_or_404(db, file_id)
    snap = _create_snapshot(db, f, vault_key, label=label or "수동 스냅샷")
    db.commit()
    db.refresh(snap)
    return SnapshotResponse(
        id=snap.id, label=snap.label, created_at=snap.created_at,
        entry_count=len(f.entries),
    )


@router.get("/{file_id}/snapshots", response_model=list[SnapshotResponse], summary="스냅샷 목록")
async def list_snapshots(
    file_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    f = _get_file_or_404(db, file_id)
    result = []
    for s in f.snapshots:
        try:
            count = len(_load_snapshot(s, vault_key))
        except ValueError:
            count = 0
        result.append(SnapshotResponse(
            id=s.id, label=s.label, created_at=s.created_at, entry_count=count,
        ))
    return result


@router.post("/{file_id}/snapshots/{snap_id}/restore", response_model=MessageResponse,
             summary="스냅샷 복원")
async def restore_snapshot(
    file_id: int,
    snap_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    f = _get_file_or_404(db, file_id)
    snap = (
        db.query(EnvFileSnapshot)
        .filter(EnvFileSnapshot.id == snap_id, EnvFileSnapshot.env_file_id == file_id)
        .first()
    )
    if not snap:
        raise AppError("err.snapshot_not_found", 404)

    try:
        rows = _load_snapshot(snap, vault_key)
    except ValueError:
        raise AppError("err.restore_failed", 400)

    # 복원 전 현재 상태를 한 번 더 스냅샷으로 보존
    if f.entries:
        _create_snapshot(db, f, vault_key, label=f"pre-restore backup (snapshot #{snap_id})")

    # 현재 엔트리 전체 교체
    for e in list(f.entries):
        db.delete(e)
    db.flush()
    for row in rows:
        db.add(EnvEntry(
            env_file_id=f.id,
            key=row["key"],
            encrypted_value=crypto.encrypt(row["value"], vault_key),
            comment=row.get("comment"),
        ))
    db.commit()
    return MessageResponse(
        message=t("msg.snapshot_restored", id=snap_id, count=len(rows))
    )


@router.get("/{file_id}/diff/{snap_id}", response_model=DiffResponse, summary="현재 vs 스냅샷 diff")
async def diff_snapshot(
    file_id: int,
    snap_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
):
    f = _get_file_or_404(db, file_id)
    snap = (
        db.query(EnvFileSnapshot)
        .filter(EnvFileSnapshot.id == snap_id, EnvFileSnapshot.env_file_id == file_id)
        .first()
    )
    if not snap:
        raise AppError("err.snapshot_not_found", 404)

    try:
        old_rows = _load_snapshot(snap, vault_key)
    except ValueError:
        raise AppError("err.diff_failed", 400)

    old_map = {r["key"]: r["value"] for r in old_rows}
    new_map = {e.key: crypto.decrypt(e.encrypted_value, vault_key) for e in f.entries}

    items: list[DiffItem] = []
    for key in sorted(set(old_map) | set(new_map)):
        old_v, new_v = old_map.get(key), new_map.get(key)
        if old_v is None:
            status_ = "added"
        elif new_v is None:
            status_ = "removed"
        elif old_v != new_v:
            status_ = "changed"
        else:
            status_ = "unchanged"
        items.append(DiffItem(
            key=key, old_value=_mask(old_v), new_value=_mask(new_v), status=status_,
        ))

    return DiffResponse(snapshot_id=snap_id, items=items)


# ──────────────────────────────────────────────────────────────
# 코드 사용처 스캔
# ──────────────────────────────────────────────────────────────

@router.post("/scan", response_model=ScanResponse, summary="로컬 경로 키 사용처 스캔")
async def scan_usage(
    req: ScanRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    root = Path(req.path)
    if not root.exists() or not root.is_dir():
        raise AppError("err.dir_not_found", 400, path=req.path)

    keys = req.keys
    if not keys:
        keys = sorted({k for (k,) in db.query(EnvEntry.key).distinct().all()})
    keys = [k for k in keys if k]
    if not keys:
        return ScanResponse(scanned_files=0, matches=[], truncated=False)

    matches: list[ScanMatch] = []
    scanned = 0
    truncated = False

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if scanned >= _SCAN_MAX_FILES:
                truncated = True
                break
            fpath = Path(dirpath) / fname
            try:
                if fpath.stat().st_size > _SCAN_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            scanned += 1
            try:
                text = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # 바이너리/접근불가 파일 건너뜀
            for lineno, line in enumerate(text.splitlines(), start=1):
                for key in keys:
                    if key in line:
                        matches.append(ScanMatch(
                            key=key,
                            file=str(fpath),
                            line_no=lineno,
                            line=line.strip()[:300],
                        ))
                        if len(matches) >= _SCAN_MAX_MATCHES:
                            truncated = True
                            break
                if len(matches) >= _SCAN_MAX_MATCHES:
                    break
            if len(matches) >= _SCAN_MAX_MATCHES:
                truncated = True
                break
        if truncated or scanned >= _SCAN_MAX_FILES:
            break

    return ScanResponse(scanned_files=scanned, matches=matches, truncated=truncated)
