"""
ENV Vault - FastAPI 애플리케이션 진입점
─────────────────────────────────────────────────────────
보안 설정:
  · 127.0.0.1 전용 바인딩 (외부 네트워크 차단)
  · HTTPS (자체 서명 SSL)
  · TrustedHostMiddleware
  · CORS 로컬 출처만 허용
  · 응답 헤더 보안 강화
─────────────────────────────────────────────────────────
"""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import auth_router
import keys_router
import envfiles_router
import test_router
from auth import cleanup_expired_revoked_tokens
from config import settings
from database import Base, SessionLocal, engine
from i18n import AppError, locale_from_request, translate
from ratelimit import limiter
from vault_state import vault


# ──────────────────────────────────────────────────────────────
# 수명 주기
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: DB 테이블 생성
    Base.metadata.create_all(bind=engine)
    # 만료된 폐기 토큰 정리 (블랙리스트 위생)
    _db = SessionLocal()
    try:
        _n = cleanup_expired_revoked_tokens(_db)
        if _n:
            print(f"🧹 만료된 폐기 토큰 {_n}건 정리")
    finally:
        _db.close()
    print(f"✅ ENV Vault {settings.VERSION} 시작")
    print(f"   📍 https://{settings.HOST}:{settings.PORT}")
    print(f"   📖 API 문서: https://{settings.HOST}:{settings.PORT}/api/docs")
    yield
    # 종료: 메모리의 Vault 키 제거
    vault.lock()
    print("🔒 Vault 잠금 완료. 서버 종료.")


# ──────────────────────────────────────────────────────────────
# 앱 생성
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="로컬 API 키 / .env 파일 보안 관리 콘솔",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# 요청 속도 제한 (slowapi) — RateLimitExceeded 는 429 로 응답
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ──────────────────────────────────────────────────────────────
# 미들웨어 (등록 순서 = 실행 역순)
# ──────────────────────────────────────────────────────────────

# 1. 신뢰 호스트 (127.0.0.1 / localhost 외 차단)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"],
)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Lang"],
    expose_headers=["X-Request-ID"],
)


# 3. 보안 응답 헤더 미들웨어
# SPA 가 토큰을 localStorage 에 보관하므로 CSP 로 XSS 표면을 강하게 제한한다.
# 모든 자원(로고 SVG 포함)을 로컬 번들로 서빙 → 외부 출처 불필요.
_CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; "   # Tailwind/React 인라인 스타일 허용
    "script-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)
# Swagger UI / ReDoc 는 CDN 자산을 로드하므로 CSP 에서 제외
_CSP_EXEMPT = ("/api/docs", "/api/redoc", "/api/openapi.json")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if not request.url.path.startswith(_CSP_EXEMPT):
        response.headers["Content-Security-Policy"] = _CSP
    # 서버 정보 숨기기 (MutableHeaders 는 pop 미지원 → 존재 시 삭제)
    if "server" in response.headers:
        del response.headers["server"]
    return response


# ──────────────────────────────────────────────────────────────
# 라우터
# ──────────────────────────────────────────────────────────────

app.include_router(auth_router.router, prefix="/api")
app.include_router(keys_router.router, prefix="/api")
app.include_router(envfiles_router.router, prefix="/api")
app.include_router(test_router.router, prefix="/api")


# ──────────────────────────────────────────────────────────────
# 전역 예외 핸들러
# ──────────────────────────────────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    # 키 기반 예외 → 요청 로케일로 번역
    locale = locale_from_request(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": translate(exc.key, locale, **exc.params)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 내부 오류 상세 정보를 외부에 노출하지 않음 (로케일별 메시지)
    locale = locale_from_request(request)
    return JSONResponse(
        status_code=500,
        content={"detail": translate("err.internal", locale)},
    )


# ──────────────────────────────────────────────────────────────
# 헬스체크 (인증 불필요)
# ──────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["시스템"])
async def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "vault_locked": not vault.is_unlocked,
    }


# ──────────────────────────────────────────────────────────────
# 프론트엔드 정적 파일 서빙
# ──────────────────────────────────────────────────────────────

_frontend_dist = Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")


# ──────────────────────────────────────────────────────────────
# 직접 실행 (python main.py)
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cert = settings.SSL_CERT_PATH
    key  = settings.SSL_KEY_PATH

    if not cert.exists() or not key.exists():
        print("❌ SSL 인증서가 없습니다. scripts/generate_certs.sh 를 먼저 실행하세요.")
        raise SystemExit(1)

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        ssl_certfile=str(cert),
        ssl_keyfile=str(key),
        reload=False,
        log_level="info",
        access_log=True,
    )
