"""
ENV Vault - 데이터베이스 모델
모든 민감 값(API 키, .env 값)은 AES-256-GCM 암호화 상태로만 저장
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from database import Base


# ──────────────────────────────────────────────────────────────
# 사용자 / 인증
# ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                = Column(Integer, primary_key=True, index=True)
    username          = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password   = Column(String(255), nullable=False)   # bcrypt
    is_active         = Column(Boolean, default=True)
    failed_attempts   = Column(Integer, default=0)
    locked_until      = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    last_login        = Column(DateTime, nullable=True)


class RevokedToken(Base):
    """로그아웃된 JWT JTI 블랙리스트"""
    __tablename__ = "revoked_tokens"

    id          = Column(Integer, primary_key=True)
    jti         = Column(String(100), unique=True, nullable=False, index=True)
    revoked_at  = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────
# API 키 관리
# ──────────────────────────────────────────────────────────────

class ApiKey(Base):
    __tablename__ = "api_keys"

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String(100), nullable=False)         # 표시명 "OpenAI 프로덕션"
    service           = Column(String(50),  nullable=False)         # "openai", "anthropic" 등
    encrypted_value   = Column(Text, nullable=False)                # AES-256-GCM 암호화값
    description       = Column(Text, nullable=True)                 # 용도 설명
    is_active         = Column(Boolean, default=True)
    tags              = Column(String(200), nullable=True)          # 쉼표 구분 태그
    expires_at        = Column(DateTime, nullable=True)             # 만료일 추적
    # 테스트 결과
    last_tested_at    = Column(DateTime, nullable=True)
    last_test_status  = Column(String(20), default="untested")      # ok / error / untested
    last_test_message = Column(Text, nullable=True)
    # 메타
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history   = relationship("ApiKeyHistory", back_populates="api_key",
                             cascade="all, delete-orphan", order_by="desc(ApiKeyHistory.changed_at)")


class ApiKeyHistory(Base):
    """API 키 변경 이력 (롤백 가능)"""
    __tablename__ = "api_key_history"

    id              = Column(Integer, primary_key=True, index=True)
    api_key_id      = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    encrypted_value = Column(Text, nullable=False)     # 변경 전 암호화값
    changed_by      = Column(String(50), nullable=True)
    note            = Column(String(200), nullable=True)
    changed_at      = Column(DateTime, default=datetime.utcnow)

    api_key = relationship("ApiKey", back_populates="history")


# ──────────────────────────────────────────────────────────────
# .env 파일 관리
# ──────────────────────────────────────────────────────────────

# API 키 ↔ .env 항목 M:N 연결 테이블
env_key_links = Table(
    "env_key_links", Base.metadata,
    Column("env_entry_id", Integer, ForeignKey("env_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("api_key_id",   Integer, ForeignKey("api_keys.id",   ondelete="CASCADE"), primary_key=True),
)


class EnvFile(Base):
    """등록된 .env 파일 (디스크 경로 연결)"""
    __tablename__ = "env_files"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)        # 표시명
    file_path     = Column(Text, nullable=False)               # 실제 경로 "/project/.env"
    project_name  = Column(String(100), nullable=True)
    environment   = Column(String(20), default="dev")          # dev / staging / prod
    last_synced_at = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    entries = relationship("EnvEntry", back_populates="env_file",
                           cascade="all, delete-orphan")
    snapshots = relationship("EnvFileSnapshot", back_populates="env_file",
                             cascade="all, delete-orphan",
                             order_by="desc(EnvFileSnapshot.created_at)")


class EnvEntry(Base):
    """개별 .env 항목 (KEY=VALUE)"""
    __tablename__ = "env_entries"

    id              = Column(Integer, primary_key=True, index=True)
    env_file_id     = Column(Integer, ForeignKey("env_files.id", ondelete="CASCADE"), nullable=False)
    key             = Column(String(100), nullable=False)      # 평문 키명 (e.g. OPENAI_API_KEY)
    encrypted_value = Column(Text, nullable=False)             # 값은 암호화 저장
    comment         = Column(Text, nullable=True)              # # 용도 메모
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    env_file = relationship("EnvFile", back_populates="entries")
    linked_api_keys = relationship("ApiKey", secondary=env_key_links)

    @property
    def linked_key_ids(self) -> list[int]:
        """연결된 API 키 ID 목록 (응답 직렬화용)"""
        return [k.id for k in self.linked_api_keys]


class EnvFileSnapshot(Base):
    """특정 시점의 .env 파일 스냅샷 (롤백용)"""
    __tablename__ = "env_file_snapshots"

    id          = Column(Integer, primary_key=True, index=True)
    env_file_id = Column(Integer, ForeignKey("env_files.id", ondelete="CASCADE"), nullable=False)
    label       = Column(String(100), nullable=True)          # "배포 전 백업" 등
    # 전체 엔트리를 JSON 직렬화 후 암호화 저장
    encrypted_snapshot = Column(Text, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    env_file = relationship("EnvFile", back_populates="snapshots")
