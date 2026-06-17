from conftest import CREDS


def test_login_rate_limited(client):
    """로그인 10/분 초과 시 429 반환 (limiter 일시 활성화)."""
    client.post("/api/auth/setup", json=CREDS)

    from ratelimit import limiter

    limiter.enabled = True
    try:
        if hasattr(limiter, "reset"):
            limiter.reset()
        codes = [
            client.post("/api/auth/login", json=CREDS).status_code
            for _ in range(12)
        ]
    finally:
        limiter.enabled = False
        if hasattr(limiter, "reset"):
            limiter.reset()

    assert 429 in codes, codes
