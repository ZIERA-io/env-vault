"""
ENV Vault - 요청 속도 제한 (brute-force 완화)
─────────────────────────────────────────────────────────
slowapi 기반. 클라이언트 IP 기준으로 인증 엔드포인트를 제한한다.
테스트에서는 ENV_VAULT_DISABLE_RATELIMIT=1 로 비활성화 가능.
─────────────────────────────────────────────────────────
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.environ.get("ENV_VAULT_DISABLE_RATELIMIT") != "1",
)
