def _create(client, auth, value="sk-ORIGINAL"):
    r = client.post(
        "/api/keys",
        headers=auth,
        json={"name": "k1", "service": "openai", "value": value},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_key_crud_value(client, auth):
    kid = _create(client, auth)
    assert client.get(f"/api/keys/{kid}/value", headers=auth).json()["value"] == "sk-ORIGINAL"
    # 목록엔 값 없음
    listed = client.get("/api/keys", headers=auth).json()
    assert "value" not in listed[0]


def test_update_creates_history_and_rollback(client, auth):
    kid = _create(client, auth)
    client.put(f"/api/keys/{kid}", headers=auth, json={"value": "sk-CHANGED"})
    assert client.get(f"/api/keys/{kid}/value", headers=auth).json()["value"] == "sk-CHANGED"

    hist = client.get(f"/api/keys/{kid}/history", headers=auth).json()
    assert len(hist) == 1
    client.post(f"/api/keys/{kid}/rollback/{hist[0]['id']}", headers=auth)
    assert client.get(f"/api/keys/{kid}/value", headers=auth).json()["value"] == "sk-ORIGINAL"


def test_delete_key(client, auth):
    kid = _create(client, auth)
    assert client.delete(f"/api/keys/{kid}", headers=auth).status_code == 200
    assert client.get(f"/api/keys/{kid}", headers=auth).status_code == 404


def test_export_import_roundtrip(client, auth):
    _create(client, auth, value="sk-EXPORTED")
    blob = client.post(
        "/api/keys/export", headers=auth, json={"backup_password": "backup-12345"}
    ).text
    # 잘못된 백업 패스워드 거부
    bad = client.post(
        "/api/keys/import",
        headers=auth,
        json={"backup_password": "wrong", "content": blob, "overwrite": True},
    )
    assert bad.status_code == 400
    # 올바른 복원
    ok = client.post(
        "/api/keys/import",
        headers=auth,
        json={"backup_password": "backup-12345", "content": blob, "overwrite": True},
    )
    assert ok.status_code == 200
    assert ok.json()["imported"] >= 1


def test_master_password_change_reencrypts(client, auth):
    kid = _create(client, auth)
    client.put(f"/api/keys/{kid}", headers=auth, json={"value": "sk-V2"})  # 이력 생성
    r = client.post(
        "/api/auth/change-master-password",
        headers=auth,
        json={
            "current_master_password": "master123456",
            "new_master_password": "new-master-999",
        },
    )
    assert r.status_code == 200
    # 변경 후에도 값/이력 복호화 가능
    assert client.get(f"/api/keys/{kid}/value", headers=auth).json()["value"] == "sk-V2"
    hist = client.get(f"/api/keys/{kid}/history", headers=auth).json()
    assert client.post(
        f"/api/keys/{kid}/rollback/{hist[-1]['id']}", headers=auth
    ).status_code == 200
