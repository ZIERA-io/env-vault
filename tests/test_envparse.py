from envparse import parse_env, serialize_env


def test_parse_basic():
    text = "KEY=value\nDB_HOST=localhost\n"
    out = parse_env(text)
    assert {e["key"]: e["value"] for e in out} == {
        "KEY": "value",
        "DB_HOST": "localhost",
    }


def test_parse_quotes_and_export_and_comments():
    text = (
        "# 단독 주석\n"
        'API_KEY="sk with spaces"  # 인라인\n'
        "export TOKEN='single'\n"
        "EMPTY=\n"
    )
    out = {e["key"]: e for e in parse_env(text)}
    assert out["API_KEY"]["value"] == "sk with spaces"
    assert out["API_KEY"]["comment"] == "단독 주석\n인라인"
    assert out["TOKEN"]["value"] == "single"
    assert out["EMPTY"]["value"] == ""


def test_blank_line_resets_comment():
    text = "# 떠다니는 주석\n\nKEY=v\n"
    out = parse_env(text)
    assert out[0]["comment"] is None


def test_serialize_roundtrip_quotes_special():
    entries = [
        {"key": "A", "value": "plain", "comment": None},
        {"key": "B", "value": "has space", "comment": "메모"},
        {"key": "C", "value": "", "comment": None},
    ]
    text = serialize_env(entries)
    reparsed = {e["key"]: e["value"] for e in parse_env(text)}
    assert reparsed == {"A": "plain", "B": "has space", "C": ""}
