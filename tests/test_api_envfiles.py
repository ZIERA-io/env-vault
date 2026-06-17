def _register(client, auth, path):
    r = client.post(
        "/api/envfiles",
        headers=auth,
        json={"name": "proj", "file_path": str(path), "environment": "dev"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_pull_entries_value_push(client, auth, tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text("# 메모\nGREETING=hello world\nDB_URL=postgres://x\n", encoding="utf-8")
    fid = _register(client, auth, envfile)

    pull = client.post(f"/api/envfiles/{fid}/sync/pull", headers=auth).json()
    assert pull["added"] == 2

    entries = client.get(f"/api/envfiles/{fid}/entries", headers=auth).json()
    g = next(e for e in entries if e["key"] == "GREETING")
    val = client.get(
        f"/api/envfiles/{fid}/entries/{g['id']}/value", headers=auth
    ).json()["value"]
    assert val == "hello world"

    # 값 수정 후 push → 디스크 반영
    client.put(
        f"/api/envfiles/{fid}/entries/{g['id']}",
        headers=auth,
        json={"value": "수정됨"},
    )
    client.post(f"/api/envfiles/{fid}/sync/push", headers=auth)
    assert "수정됨" in envfile.read_text(encoding="utf-8")


def test_snapshot_diff_restore(client, auth, tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text("GREETING=hello\n", encoding="utf-8")
    fid = _register(client, auth, envfile)
    client.post(f"/api/envfiles/{fid}/sync/pull", headers=auth)

    snap = client.post(f"/api/envfiles/{fid}/snapshot", headers=auth).json()
    entries = client.get(f"/api/envfiles/{fid}/entries", headers=auth).json()
    g = entries[0]
    client.put(
        f"/api/envfiles/{fid}/entries/{g['id']}", headers=auth, json={"value": "changed"}
    )

    diff = client.get(f"/api/envfiles/{fid}/diff/{snap['id']}", headers=auth).json()
    changed = next(i for i in diff["items"] if i["key"] == "GREETING")
    assert changed["status"] == "changed"

    client.post(
        f"/api/envfiles/{fid}/snapshots/{snap['id']}/restore", headers=auth
    )
    entries2 = client.get(f"/api/envfiles/{fid}/entries", headers=auth).json()
    g2 = entries2[0]
    val = client.get(
        f"/api/envfiles/{fid}/entries/{g2['id']}/value", headers=auth
    ).json()["value"]
    assert val == "hello"


def test_scan(client, auth, tmp_path):
    (tmp_path / "app.py").write_text("x = os.environ['GREETING']\n", encoding="utf-8")
    r = client.post(
        "/api/envfiles/scan",
        headers=auth,
        json={"path": str(tmp_path), "keys": ["GREETING"]},
    )
    assert r.status_code == 200
    assert any(m["key"] == "GREETING" for m in r.json()["matches"])


def test_key_entry_links(client, auth, tmp_path):
    envfile = tmp_path / ".env"
    envfile.write_text("GREETING=hello\n", encoding="utf-8")
    fid = _register(client, auth, envfile)
    client.post(f"/api/envfiles/{fid}/sync/pull", headers=auth)
    eid = client.get(f"/api/envfiles/{fid}/entries", headers=auth).json()[0]["id"]

    kid = client.post(
        "/api/keys",
        headers=auth,
        json={"name": "linked", "service": "openai", "value": "sk-x"},
    ).json()["id"]

    # 연결
    assert client.post(
        f"/api/envfiles/{fid}/entries/{eid}/links/{kid}", headers=auth
    ).status_code == 200
    links = client.get(
        f"/api/envfiles/{fid}/entries/{eid}/links", headers=auth
    ).json()
    assert [k["id"] for k in links] == [kid]
    # 엔트리 응답에 linked_key_ids 반영
    entry = client.get(f"/api/envfiles/{fid}/entries", headers=auth).json()[0]
    assert kid in entry["linked_key_ids"]

    # 해제
    assert client.delete(
        f"/api/envfiles/{fid}/entries/{eid}/links/{kid}", headers=auth
    ).status_code == 200
    links2 = client.get(
        f"/api/envfiles/{fid}/entries/{eid}/links", headers=auth
    ).json()
    assert links2 == []
