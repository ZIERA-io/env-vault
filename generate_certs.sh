#!/bin/bash
# ─────────────────────────────────────────────────────────────
# ENV Vault - 로컬용 자체 서명 SSL 인증서 생성
# RSA 4096bit / SHA-256 / 유효기간 10년
# SAN(Subject Alt Name)으로 127.0.0.1, localhost 모두 커버
# ─────────────────────────────────────────────────────────────

set -e

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "✅ SSL 인증서가 이미 존재합니다: $CERT_DIR"
    exit 0
fi

echo "📜 SSL 인증서 생성 중 (RSA 4096)..."

openssl req -x509 \
    -newkey rsa:4096 \
    -sha256 \
    -days 3650 \
    -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=ENV Vault/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "✅ 인증서 생성 완료:"
echo "   cert: $CERT_FILE"
echo "   key:  $KEY_FILE"
echo ""
echo "⚠️  브라우저에서 '안전하지 않은 연결' 경고가 표시될 수 있습니다."
echo "   로컬 전용 앱이므로 예외 추가(고급 → 계속 진행)하면 됩니다."
