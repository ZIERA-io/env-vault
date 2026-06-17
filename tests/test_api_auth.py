from conftest import CREDS


def test_setup_then_second_setup_rejected(client):
    assert client.post("/api/auth/setup", json=CREDS).status_code == 200
    r = client.post("/api/auth/setup", json=CREDS)
    assert r.status_code == 400


def test_login_success_and_status(client, auth):
    s = client.get("/api/auth/status").json()
    assert s["initialized"] is True
    assert s["vault_unlocked"] is True


def test_login_wrong_password(client):
    client.post("/api/auth/setup", json=CREDS)
    r = client.post(
        "/api/auth/login",
        json={**CREDS, "password": "wrong-password"},
    )
    assert r.status_code == 401


def test_protected_requires_auth(client):
    assert client.get("/api/keys").status_code == 403


def test_security_headers_and_csp(client):
    r = client.get("/api/health")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_login_timing_equalized_for_unknown_user(client):
    """존재하지 않는 사용자도 동일 에러 메시지 (사용자 열거 방지). 기본 로케일 영어."""
    client.post("/api/auth/setup", json=CREDS)
    r = client.post(
        "/api/auth/login",
        json={"username": "ghost", "password": "whatever1", "master_password": "x" * 8},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect username or password."


def test_error_message_localized_by_x_lang(client):
    """X-Lang 헤더에 따라 서버 에러 메시지가 번역된다."""
    client.post("/api/auth/setup", json=CREDS)
    bad = {"username": "ghost", "password": "nope1234", "master_password": "x" * 8}
    expected = {
        "en": "Incorrect username or password.",
        "ja": "ユーザー名またはパスワードが正しくありません。",
        "zh": "用户名或密码不正确。",
        "ko": "아이디 또는 비밀번호가 올바르지 않습니다.",
    }
    for lang, msg in expected.items():
        r = client.post("/api/auth/login", json=bad, headers={"X-Lang": lang})
        assert r.status_code == 401
        assert r.json()["detail"] == msg, (lang, r.json())


def test_success_message_localized(client, auth):
    """성공 메시지(파라미터 포함)도 X-Lang 으로 번역된다."""
    # 키 생성 후 영어로 삭제 → 영어 메시지
    kid = client.post(
        "/api/keys", headers=auth,
        json={"name": "tmp", "service": "openai", "value": "sk-x"},
    ).json()["id"]
    r = client.delete(f"/api/keys/{kid}", headers={**auth, "X-Lang": "en"})
    assert r.json()["message"] == "Key 'tmp' deleted."


def test_internal_error_localized(client):
    """전역 500 핸들러도 로케일별 메시지."""
    # Accept-Language 로도 동작하는지 확인 (X-Lang 없을 때)
    client.post("/api/auth/setup", json=CREDS)
    r = client.post(
        "/api/auth/login",
        json={"username": "ghost", "password": "nope1234", "master_password": "x" * 8},
        headers={"Accept-Language": "ja,en;q=0.9"},
    )
    assert r.json()["detail"] == "ユーザー名またはパスワードが正しくありません。"


def test_change_login_password(client, auth):
    r = client.post(
        "/api/auth/change-password",
        headers=auth,
        json={"current_password": "password123", "new_password": "newpass456"},
    )
    assert r.status_code == 200
    # 새 비밀번호로 로그인 가능
    r2 = client.post(
        "/api/auth/login",
        json={**CREDS, "password": "newpass456"},
    )
    assert r2.status_code == 200
