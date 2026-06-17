"""
ENV Vault - 암호화 모듈
─────────────────────────────────────────────────────────
알고리즘: AES-256-GCM  (인증 암호화, 변조 감지 내장)
키 유도:  PBKDF2-SHA256 / 600,000 iterations (NIST SP 800-132)
         마스터 패스워드 + 랜덤 32바이트 salt → 32바이트 Vault 키
검증:     알려진 평문을 암호화해 .vault_verify 에 저장
         잠금 해제 시 복호화 결과 비교
─────────────────────────────────────────────────────────
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag
from config import settings
from i18n import AppError

# 마스터 패스워드 검증에 사용할 알려진 평문
_VERIFY_MAGIC = b"ENV_VAULT_UNLOCKED_v1"


# ──────────────────────────────────────────────────────────────
# 키 유도
# ──────────────────────────────────────────────────────────────

def _derive_key(master_password: str, salt: bytes) -> bytes:
    """
    PBKDF2-SHA256 (600,000 iter) 으로 마스터 패스워드 → 32바이트 AES 키 유도
    600,000 회는 2023년 OWASP 권고 기준
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(master_password.encode("utf-8"))


# ──────────────────────────────────────────────────────────────
# 암복호화 원시 함수
# ──────────────────────────────────────────────────────────────

def encrypt(plaintext: str, vault_key: bytes) -> str:
    """
    AES-256-GCM 암호화
    출력: base64url(nonce[12] || ciphertext+tag)
    nonce는 매번 랜덤 생성 (재사용 방지)
    """
    aesgcm = AESGCM(vault_key)
    nonce = os.urandom(12)          # GCM 권장 96-bit nonce
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt(encrypted: str, vault_key: bytes) -> str:
    """
    AES-256-GCM 복호화
    인증 태그 불일치 시 InvalidTag 예외 → ValueError 로 래핑
    """
    try:
        raw = base64.urlsafe_b64decode(encrypted.encode("ascii"))
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(vault_key)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
    except InvalidTag:
        raise ValueError("복호화 실패: 키가 올바르지 않거나 데이터가 손상되었습니다.")
    except Exception as e:
        raise ValueError(f"복호화 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 패스워드 기반 자가완결 암복호화 (백업 export/import 용)
# ── Vault 키와 무관하게, 백업 파일 자체에 salt 를 포함시켜
#    다른 환경에서도 복원 가능하도록 한다.
# ──────────────────────────────────────────────────────────────

def encrypt_with_password(plaintext: str, password: str) -> str:
    """
    백업용: salt 를 산출물에 포함하는 자가완결 암호화
    출력: base64url(salt[16] || nonce[12] || ciphertext+tag)
    """
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(salt + nonce + ct).decode("ascii")


def decrypt_with_password(blob: str, password: str) -> str:
    """encrypt_with_password 산출물을 복호화 (백업 패스워드 검증 포함)"""
    try:
        raw = base64.urlsafe_b64decode(blob.encode("ascii"))
        salt, nonce, ct = raw[:16], raw[16:28], raw[28:]
        key = _derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
    except InvalidTag:
        raise ValueError("백업 복호화 실패: 백업 패스워드가 올바르지 않거나 파일이 손상되었습니다.")
    except Exception as e:
        raise ValueError(f"백업 복호화 오류: {e}")


# ──────────────────────────────────────────────────────────────
# Vault 초기화 / 잠금 해제
# ──────────────────────────────────────────────────────────────

def is_vault_initialized() -> bool:
    """salt 파일과 검증 파일이 모두 존재하면 초기화된 상태"""
    return (
        settings.VAULT_SALT_PATH.exists() and
        settings.VAULT_VERIFY_PATH.exists()
    )


def initialize_vault(master_password: str) -> bytes:
    """
    최초 설정:
    1) 32바이트 랜덤 salt 생성
    2) 마스터 패스워드로 Vault 키 유도
    3) 검증 토큰 저장 (이후 unlock 시 패스워드 검증에 사용)
    반환: vault_key (bytes)
    """
    if is_vault_initialized():
        raise AppError("err.vault_already_init", 400)

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    salt = os.urandom(32)
    vault_key = _derive_key(master_password, salt)

    # salt 저장 (소유자만 읽기)
    settings.VAULT_SALT_PATH.write_bytes(salt)
    settings.VAULT_SALT_PATH.chmod(0o600)

    # 검증 토큰 저장
    verify_token = encrypt(_VERIFY_MAGIC.decode("utf-8"), vault_key)
    settings.VAULT_VERIFY_PATH.write_text(verify_token, encoding="utf-8")
    settings.VAULT_VERIFY_PATH.chmod(0o600)

    return vault_key


def unlock_vault(master_password: str) -> bytes:
    """
    마스터 패스워드 검증 후 Vault 키 반환
    검증 실패 시 ValueError
    """
    if not is_vault_initialized():
        raise AppError("err.vault_not_init", 400)

    salt = settings.VAULT_SALT_PATH.read_bytes()
    vault_key = _derive_key(master_password, salt)

    verify_token = settings.VAULT_VERIFY_PATH.read_text(encoding="utf-8")
    try:
        result = decrypt(verify_token, vault_key)
    except ValueError:
        raise AppError("err.bad_master", 401)

    if result != _VERIFY_MAGIC.decode("utf-8"):
        raise AppError("err.bad_master", 401)

    return vault_key


def change_master_password(
    old_password: str,
    new_password: str,
    all_encrypted_values: list[str],
) -> tuple[bytes, list[str]]:
    """
    마스터 패스워드 변경:
    1) 기존 PW로 모든 암호화값 복호화
    2) 새 salt + 새 PW로 재암호화
    반환: (new_vault_key, re_encrypted_values)
    """
    old_key = unlock_vault(old_password)

    # 기존 데이터 복호화
    plaintexts = [decrypt(v, old_key) for v in all_encrypted_values]

    # 기존 파일 삭제 후 재초기화
    settings.VAULT_SALT_PATH.unlink(missing_ok=True)
    settings.VAULT_VERIFY_PATH.unlink(missing_ok=True)

    new_key = initialize_vault(new_password)

    # 새 키로 재암호화
    re_encrypted = [encrypt(p, new_key) for p in plaintexts]

    return new_key, re_encrypted
