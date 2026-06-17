"""
ENV Vault - Pydantic 스키마
요청 검증 및 응답 직렬화
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


# ──────────────────────────────────────────────────────────────
# 인증
# ──────────────────────────────────────────────────────────────

class SetupRequest(BaseModel):
    username:        str = Field(..., min_length=3, max_length=50)
    password:        str = Field(..., min_length=8, max_length=128)
    master_password: str = Field(..., min_length=8, max_length=128,
                                  description="Vault 암호화 키 유도용 마스터 패스워드")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("아이디는 영문/숫자/_/- 만 사용 가능합니다.")
        return v


class LoginRequest(BaseModel):
    username:        str = Field(..., min_length=1)
    password:        str = Field(..., min_length=1)
    master_password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int = Field(default=900, description="액세스 토큰 만료(초)")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str = Field(..., min_length=8, max_length=128)


class ChangeMasterPasswordRequest(BaseModel):
    current_master_password: str
    new_master_password:     str = Field(..., min_length=8, max_length=128)


# ──────────────────────────────────────────────────────────────
# API 키
# ──────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name:        str = Field(..., min_length=1, max_length=100)
    service:     str = Field(..., max_length=50)
    value:       str = Field(..., min_length=1, description="평문 API 키 값 (저장 시 암호화됨)")
    description: Optional[str] = None
    tags:        Optional[str] = None     # 쉼표 구분 "prod,payment"
    expires_at:  Optional[datetime] = None


class ApiKeyUpdate(BaseModel):
    name:        Optional[str] = Field(None, max_length=100)
    service:     Optional[str] = Field(None, max_length=50)
    value:       Optional[str] = Field(None, description="새 값 (None이면 유지)")
    description: Optional[str] = None
    tags:        Optional[str] = None
    expires_at:  Optional[datetime] = None
    is_active:   Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id:               int
    name:             str
    service:          str
    description:      Optional[str]
    is_active:        bool
    tags:             Optional[str]
    expires_at:       Optional[datetime]
    last_tested_at:   Optional[datetime]
    last_test_status: str
    last_test_message: Optional[str]
    created_at:       datetime
    updated_at:       datetime

    class Config:
        from_attributes = True


class ApiKeyWithValue(ApiKeyResponse):
    """복호화된 값 포함 (명시적 요청 시에만 반환)"""
    value: str


class ApiKeyHistoryItem(BaseModel):
    id:         int
    changed_by: Optional[str]
    note:       Optional[str]
    changed_at: datetime

    class Config:
        from_attributes = True


class ApiKeyExportRequest(BaseModel):
    backup_password: str = Field(..., min_length=8, max_length=128,
                                 description="백업 파일 전용 패스워드 (마스터 PW와 무관)")


class ApiKeyImportRequest(BaseModel):
    backup_password: str = Field(..., min_length=1)
    content:         str = Field(..., description="export 로 받은 .envbackup 파일 내용")
    overwrite:       bool = Field(default=False, description="동일 name+service 키 덮어쓰기 여부")


class ApiKeyImportResult(BaseModel):
    imported: int
    skipped:  int
    message:  str


# ──────────────────────────────────────────────────────────────
# .env 파일
# ──────────────────────────────────────────────────────────────

class EnvFileCreate(BaseModel):
    name:         str = Field(..., min_length=1, max_length=100)
    file_path:    str = Field(..., description="디스크 절대경로 /project/.env")
    project_name: Optional[str] = Field(None, max_length=100)
    environment:  str = Field(default="dev", pattern="^(dev|staging|prod|test)$")


class EnvEntryCreate(BaseModel):
    key:     str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Z_][A-Z0-9_]*$")
    value:   str = Field(..., description="평문 값 (저장 시 암호화됨)")
    comment: Optional[str] = None


class EnvEntryUpdate(BaseModel):
    value:   Optional[str] = None
    comment: Optional[str] = None


class EnvEntryResponse(BaseModel):
    id:         int
    key:        str
    comment:    Optional[str]
    created_at: datetime
    updated_at: datetime
    linked_key_ids: list[int] = []   # 연결된 API 키 ID
    # value 는 별도 엔드포인트에서만 반환

    class Config:
        from_attributes = True


class EnvEntryWithValue(EnvEntryResponse):
    """복호화된 값 포함 (명시적 요청 시에만 반환)"""
    value: str


class EnvFileResponse(BaseModel):
    id:             int
    name:           str
    file_path:      str
    project_name:   Optional[str]
    environment:    str
    last_synced_at: Optional[datetime]
    created_at:     datetime
    entry_count:    int = 0
    file_exists:    bool = False

    class Config:
        from_attributes = True


class EnvFileDetailResponse(EnvFileResponse):
    """파일 상세 + 엔트리 목록 (값 제외)"""
    entries: list[EnvEntryResponse] = []


class SyncResult(BaseModel):
    direction: str            # "pull" | "push"
    added:     int = 0
    updated:   int = 0
    kept:      int = 0
    removed:   int = 0
    message:   str


class SnapshotResponse(BaseModel):
    id:         int
    label:      Optional[str]
    created_at: datetime
    entry_count: int = 0

    class Config:
        from_attributes = True


class DiffItem(BaseModel):
    key:       str
    old_value: Optional[str]   # 마스킹된 값
    new_value: Optional[str]   # 마스킹된 값
    status:    str             # added | removed | changed | unchanged


class DiffResponse(BaseModel):
    snapshot_id: int
    items:       list[DiffItem]


class ScanRequest(BaseModel):
    path: str = Field(..., description="스캔할 로컬 디렉토리 절대경로")
    keys: Optional[list[str]] = Field(None, description="검색할 키 이름 목록 (없으면 등록된 전체 키)")


class ScanMatch(BaseModel):
    key:      str
    file:     str
    line_no:  int
    line:     str


class ScanResponse(BaseModel):
    scanned_files: int
    matches:       list[ScanMatch]
    truncated:     bool = False


# ──────────────────────────────────────────────────────────────
# API 키 테스트
# ──────────────────────────────────────────────────────────────

class ServiceInfo(BaseModel):
    service:   str
    label:     str
    test_url:  Optional[str] = None
    has_usage: bool = False


class TestResult(BaseModel):
    key_id:      int
    service:     str
    status:      str            # ok | error | unsupported
    message:     str
    tested_at:   datetime


class BatchTestRequest(BaseModel):
    key_ids: list[int] = Field(..., min_length=1)


class UsageResult(BaseModel):
    key_id:  int
    service: str
    status:  str               # ok | error | unsupported
    message: str
    data:    Optional[dict] = None


# ──────────────────────────────────────────────────────────────
# 공통
# ──────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class VaultStatusResponse(BaseModel):
    initialized:    bool
    vault_unlocked: bool
    unlocked_at:    Optional[datetime]
    idle_seconds:   Optional[float]
    timeout_minutes: int
