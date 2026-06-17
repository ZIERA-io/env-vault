"""
ENV Vault - .env 파서 / 직렬화
─────────────────────────────────────────────────────────
지원 포맷:
  KEY=VALUE
  KEY="VALUE WITH SPACES"
  KEY='VALUE'
  export KEY=VALUE        # export 키워드 무시
  # 주석                  # 다음 KEY 에 메모로 보존
  KEY=VALUE  # 인라인 주석  # 값 뒤 인라인 주석도 보존
무시: 빈 줄
─────────────────────────────────────────────────────────
"""

from typing import Optional


def _split_value_comment(s: str) -> tuple[str, Optional[str]]:
    """`=` 우변에서 값과 인라인 주석을 분리한다."""
    s = s.strip()
    if not s:
        return "", None

    # 따옴표로 감싼 값: 닫는 따옴표 이후의 # 만 주석으로 취급
    if s[0] in ("'", '"'):
        quote = s[0]
        end = s.find(quote, 1)
        if end != -1:
            value = s[1:end]
            after = s[end + 1:].strip()
            comment = after.lstrip("#").strip() if after.startswith("#") else None
            return value, comment
        # 닫는 따옴표가 없으면 따옴표 제거 후 전체를 값으로
        return s[1:], None

    # 비따옴표 값: " #" 위치에서 인라인 주석 분리
    idx = s.find(" #")
    if idx != -1:
        return s[:idx].strip(), s[idx + 2:].strip() or None
    return s, None


def parse_env(text: str) -> list[dict]:
    """
    .env 텍스트를 [{key, value, comment}] 리스트로 파싱.
    단독 주석 줄(#...)은 바로 다음 KEY 의 comment 로 붙는다.
    빈 줄은 누적된 주석 블록을 리셋한다.
    """
    entries: list[dict] = []
    pending: list[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            pending = []
            continue
        if line.startswith("#"):
            pending.append(line.lstrip("#").strip())
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue

        key, _, rest = line.partition("=")
        key = key.strip()
        if not key:
            continue

        value, inline = _split_value_comment(rest)
        parts = list(pending)
        if inline:
            parts.append(inline)
        entries.append({
            "key": key,
            "value": value,
            "comment": "\n".join(parts) if parts else None,
        })
        pending = []

    return entries


def _needs_quoting(value: str) -> bool:
    if value == "":
        return True
    return any(c in value for c in (" ", "\t", "#", '"', "'", "=", "\n"))


def serialize_env(entries: list[dict]) -> str:
    """
    [{key, value, comment}] → .env 텍스트.
    comment 는 KEY 위에 `# ...` 줄로 복원, 특수문자 포함 값은 큰따옴표 처리.
    """
    lines: list[str] = []
    for e in entries:
        comment = e.get("comment")
        if comment:
            for cline in str(comment).split("\n"):
                lines.append(f"# {cline}")
        value = e.get("value", "")
        if _needs_quoting(value):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            value = f'"{escaped}"'
        lines.append(f'{e["key"]}={value}')
    return "\n".join(lines) + ("\n" if lines else "")
