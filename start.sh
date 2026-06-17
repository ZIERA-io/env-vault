#!/bin/bash
# ─────────────────────────────────────────────────────────────
# ENV Vault - 시작 스크립트 (평면 레이아웃)
# 1) SSL 인증서 없으면 자동 생성
# 2) 가상환경 없으면 생성 + 의존성 설치
# 3) 서버 실행
# ─────────────────────────────────────────────────────────────

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

echo "🔐 ENV Vault 시작 중..."
echo "   경로: $ROOT_DIR"

# ── SSL 인증서 ────────────────────────────────────────────────
if [ ! -f "$ROOT_DIR/certs/cert.pem" ]; then
    echo ""
    echo "📜 SSL 인증서 생성 중..."
    bash "$ROOT_DIR/generate_certs.sh"
fi

# ── Python 가상환경 ───────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "📦 가상환경 생성 중..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 의존성 설치 ───────────────────────────────────────────────
echo ""
echo "📦 의존성 확인 중..."
pip install -q -r "$ROOT_DIR/requirements.txt"

# ── 프론트엔드 빌드 (dist 없고 npm 있을 때만) ─────────────────
FRONTEND_DIR="$ROOT_DIR/frontend"
if [ ! -f "$FRONTEND_DIR/dist/index.html" ] && command -v npm >/dev/null 2>&1; then
    echo ""
    echo "🎨 프론트엔드 빌드 중..."
    (cd "$FRONTEND_DIR" && npm install --silent && npm run build)
fi

# ── 서버 실행 ─────────────────────────────────────────────────
echo ""
echo "🚀 서버 시작 중..."
echo "   접속 주소: https://127.0.0.1:8443"
echo "   API 문서:  https://127.0.0.1:8443/api/docs"
echo "   종료:      Ctrl+C"
echo ""

cd "$ROOT_DIR"
python main.py
