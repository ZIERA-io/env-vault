"""
ENV Vault - API 키 테스트 라우터
─────────────────────────────────────────────────────────
POST /api/test/key/{id}    단일 키 테스트 (서비스 자동 감지)
POST /api/test/batch       여러 키 일괄 테스트
GET  /api/test/services    지원 서비스 목록
POST /api/test/usage/{id}  API 사용량 불러오기 (지원 서비스 한정)
─────────────────────────────────────────────────────────
실제 평문 키는 메모리에서만 다루며, 외부 서비스의 인증 엔드포인트로만 전송한다.
"""

import asyncio
import base64
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import crypto
from database import get_db
from dependencies import get_current_user, get_vault_key
from i18n import AppError, get_translator
from models import ApiKey, User
from schemas import (
    BatchTestRequest, ServiceInfo, TestResult, UsageResult,
)

router = APIRouter(prefix="/test", tags=["키 테스트"])

_TIMEOUT = 10.0


def _bearer(k: str) -> dict:
    return {"Authorization": f"Bearer {k}"}


def _basic(k: str) -> dict:
    token = base64.b64encode(f"{k}:".encode()).decode()
    return {"Authorization": f"Basic {token}"}


# 서비스별 감지 규칙 + 테스트/사용량 엔드포인트
# test/usage: (method, url, headers) 를 만드는 콜백
SERVICES: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "detect": lambda k: k.startswith("sk-") and not k.startswith("sk-ant-"),
        "test_url": "https://api.openai.com/v1/models",
        "test": lambda k: ("GET", "https://api.openai.com/v1/models", _bearer(k)),
        "usage": lambda k: ("GET", "https://api.openai.com/v1/usage", _bearer(k)),
    },
    "anthropic": {
        "label": "Anthropic",
        "detect": lambda k: k.startswith("sk-ant-"),
        "test_url": "https://api.anthropic.com/v1/models",
        "test": lambda k: ("GET", "https://api.anthropic.com/v1/models",
                           {"x-api-key": k, "anthropic-version": "2023-06-01"}),
    },
    "github": {
        "label": "GitHub",
        "detect": lambda k: k.startswith(("ghp_", "github_pat_", "gho_", "ghu_")),
        "test_url": "https://api.github.com/user",
        "test": lambda k: ("GET", "https://api.github.com/user",
                           {**_bearer(k), "Accept": "application/vnd.github+json"}),
    },
    "google": {
        "label": "Google AI",
        "detect": lambda k: len(k) == 39 and k.startswith("AIza"),
        "test_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "test": lambda k: ("GET",
                           f"https://generativelanguage.googleapis.com/v1beta/models?key={k}",
                           {}),
    },
    "stripe": {
        "label": "Stripe",
        "detect": lambda k: k.startswith(("sk_live_", "sk_test_", "rk_live_", "rk_test_")),
        "test_url": "https://api.stripe.com/v1/balance",
        "test": lambda k: ("GET", "https://api.stripe.com/v1/balance", _basic(k)),
    },
}


def detect_service(value: str) -> Optional[str]:
    for name, cfg in SERVICES.items():
        if cfg["detect"](value):
            return name
    return None


# 반환: (status, 메시지키, 파라미터) — 엔드포인트에서 로케일로 번역
def _interpret(code: int) -> tuple[str, str, dict]:
    if 200 <= code < 300:
        return "ok", "test.ok", {"code": code}
    if code in (401, 403):
        return "error", "test.auth_fail", {"code": code}
    if code == 429:
        return "ok", "test.rate_limited", {"code": code}
    return "error", "test.unexpected", {"code": code}


async def _run_test(client: httpx.AsyncClient, service: str, value: str) -> tuple[str, str, dict]:
    cfg = SERVICES.get(service)
    if not cfg:
        return "unsupported", "test.unsupported", {"service": service}
    method, url, headers = cfg["test"](value)
    try:
        resp = await client.request(method, url, headers=headers)
    except httpx.RequestError as e:
        return "error", "test.network_err", {"err": e.__class__.__name__}
    return _interpret(resp.status_code)


def _resolve_service(key: ApiKey, value: str) -> Optional[str]:
    if key.service in SERVICES:
        return key.service
    return detect_service(value)


def _persist(db: Session, key: ApiKey, status_: str, message: str, when: datetime) -> None:
    # DB 의 last_test_status 는 ok / error / untested 만 사용
    key.last_test_status = status_ if status_ in ("ok", "error") else "untested"
    key.last_test_message = message
    key.last_tested_at = when


# ──────────────────────────────────────────────────────────────
# 지원 서비스 목록
# ──────────────────────────────────────────────────────────────

@router.get("/services", response_model=list[ServiceInfo], summary="지원 서비스 목록")
async def list_services(_: User = Depends(get_current_user)):
    return [
        ServiceInfo(
            service=name,
            label=cfg["label"],
            test_url=cfg.get("test_url"),
            has_usage="usage" in cfg,
        )
        for name, cfg in SERVICES.items()
    ]


# ──────────────────────────────────────────────────────────────
# 단일 / 배치 테스트
# ──────────────────────────────────────────────────────────────

@router.post("/key/{key_id}", response_model=TestResult, summary="단일 키 테스트")
async def test_key(
    key_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise AppError("err.key_not_found", 404)

    value = crypto.decrypt(key.encrypted_value, vault_key)
    service = _resolve_service(key, value)

    now = datetime.utcnow()
    if not service:
        status_, mkey, params = "unsupported", "test.detect_fail", {}
    else:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            status_, mkey, params = await _run_test(client, service, value)

    message = t(mkey, **params)
    _persist(db, key, status_, message, now)
    db.commit()
    return TestResult(
        key_id=key.id, service=service or key.service,
        status=status_, message=message, tested_at=now,
    )


@router.post("/batch", response_model=list[TestResult], summary="여러 키 일괄 테스트")
async def test_batch(
    req: BatchTestRequest,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    keys = db.query(ApiKey).filter(ApiKey.id.in_(req.key_ids)).all()
    if not keys:
        raise AppError("err.key_not_found", 404)

    now = datetime.utcnow()
    # 먼저 복호화 + 서비스 판별 (네트워크 호출 전)
    plans = []
    for key in keys:
        value = crypto.decrypt(key.encrypted_value, vault_key)
        plans.append((key, _resolve_service(key, value), value))

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        async def _one(service, value):
            if not service:
                return "unsupported", "test.detect_fail_short", {}
            return await _run_test(client, service, value)

        outcomes = await asyncio.gather(
            *[_one(service, value) for (_, service, value) in plans]
        )

    results: list[TestResult] = []
    for (key, service, _), (status_, mkey, params) in zip(plans, outcomes):
        message = t(mkey, **params)
        _persist(db, key, status_, message, now)
        results.append(TestResult(
            key_id=key.id, service=service or key.service,
            status=status_, message=message, tested_at=now,
        ))
    db.commit()
    return results


# ──────────────────────────────────────────────────────────────
# 사용량
# ──────────────────────────────────────────────────────────────

@router.post("/usage/{key_id}", response_model=UsageResult, summary="API 사용량 불러오기")
async def fetch_usage(
    key_id: int,
    vault_key: bytes = Depends(get_vault_key),
    db: Session = Depends(get_db),
    t=Depends(get_translator),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise AppError("err.key_not_found", 404)

    value = crypto.decrypt(key.encrypted_value, vault_key)
    service = _resolve_service(key, value)
    cfg = SERVICES.get(service or "")

    if not cfg or "usage" not in cfg:
        return UsageResult(
            key_id=key.id, service=service or key.service,
            status="unsupported",
            message=t("usage.unsupported"),
        )

    method, url, headers = cfg["usage"](value)
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.request(method, url, headers=headers)
        except httpx.RequestError as e:
            return UsageResult(
                key_id=key.id, service=service, status="error",
                message=t("usage.network_err", err=e.__class__.__name__),
            )

    if 200 <= resp.status_code < 300:
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text[:2000]}
        return UsageResult(
            key_id=key.id, service=service, status="ok",
            message=t("usage.ok"), data=data,
        )

    return UsageResult(
        key_id=key.id, service=service, status="error",
        message=t("usage.failed", code=resp.status_code),
    )
