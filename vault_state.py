"""
ENV Vault - 인메모리 Vault 키 상태 관리
─────────────────────────────────────────────────────────
Vault 키는 절대 디스크에 평문 저장하지 않음
로그인 후 메모리에만 유지, 다음 경우 자동 잠금:
  - 로그아웃
  - 비활성 SESSION_TIMEOUT_MINUTES 초과
  - 서버 재시작
─────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from typing import Optional
from config import settings


class VaultState:
    def __init__(self):
        self._key: Optional[bytes] = None
        self._unlocked_at: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None

    # ── 잠금 / 해제 ──────────────────────────────────────

    def unlock(self, vault_key: bytes) -> None:
        self._key = vault_key
        now = datetime.utcnow()
        self._unlocked_at = now
        self._last_activity = now

    def lock(self) -> None:
        """키를 메모리에서 제거 (덮어쓰기로 흔적 최소화)"""
        if self._key:
            # bytes는 불변이라 직접 덮기 불가, 참조만 제거
            self._key = None
        self._unlocked_at = None
        self._last_activity = None

    # ── 상태 확인 ─────────────────────────────────────────

    @property
    def is_unlocked(self) -> bool:
        if self._key is None:
            return False
        # 비활성 타임아웃 체크
        if self._last_activity:
            timeout = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES)
            if datetime.utcnow() - self._last_activity > timeout:
                self.lock()
                return False
        return True

    @property
    def unlocked_at(self) -> Optional[datetime]:
        return self._unlocked_at

    @property
    def idle_seconds(self) -> Optional[float]:
        if self._last_activity:
            return (datetime.utcnow() - self._last_activity).total_seconds()
        return None

    # ── 키 접근 ──────────────────────────────────────────

    def get_key(self) -> bytes:
        """
        Vault 키 반환 + 마지막 활동 시간 갱신
        잠긴 상태면 RuntimeError
        """
        if not self.is_unlocked:
            raise RuntimeError("Vault가 잠겨 있습니다. 다시 로그인해주세요.")
        self._last_activity = datetime.utcnow()
        return self._key

    def status(self) -> dict:
        return {
            "unlocked": self.is_unlocked,
            "unlocked_at": self._unlocked_at.isoformat() if self._unlocked_at else None,
            "idle_seconds": self.idle_seconds,
            "timeout_minutes": settings.SESSION_TIMEOUT_MINUTES,
        }


# 프로세스 전역 싱글톤
vault = VaultState()
