"""
ENV Vault - 백엔드 다국어 (서버 응답 메시지)
─────────────────────────────────────────────────────────
· AppError(key, status_code, **params) 로 메시지 키를 던지고,
  전역 핸들러가 요청 로케일로 번역해 응답한다.
· 성공 메시지는 get_translator 의존성의 t(key, **params) 로 번역.
· 로케일 결정: X-Lang 헤더 → Accept-Language → 기본(ko)
  (브라우저는 JS 로 Accept-Language 변경 불가 → 프론트가 X-Lang 전송)
─────────────────────────────────────────────────────────
"""

from fastapi import Request

SUPPORTED = ("en", "ko", "ja", "zh")
DEFAULT_LOCALE = "en"


# ──────────────────────────────────────────────────────────────
# 메시지 사전 (모든 로케일 동일 키)
# ──────────────────────────────────────────────────────────────

MESSAGES = {
    "ko": {
        # 에러
        "err.internal": "내부 서버 오류가 발생했습니다.",
        "err.wrong_credentials": "아이디 또는 비밀번호가 올바르지 않습니다.",
        "err.account_locked": "계정이 잠겼습니다. {minutes}분 후 다시 시도하세요.",
        "err.too_many_attempts": "로그인 시도가 {max}회 초과되었습니다. {lockout}분 후 다시 시도하세요.",
        "err.bad_master": "마스터 패스워드가 올바르지 않습니다.",
        "err.vault_not_init": "Vault가 초기화되지 않았습니다. 먼저 설정을 완료하세요.",
        "err.vault_already_init": "Vault가 이미 초기화되어 있습니다.",
        "err.vault_locked": "Vault가 잠겼습니다. 다시 로그인해주세요.",
        "err.setup_done": "이미 설정이 완료되었습니다.",
        "err.invalid_token": "유효하지 않은 토큰입니다.",
        "err.logged_out_token": "이미 로그아웃된 토큰입니다.",
        "err.token_type": "토큰 타입이 올바르지 않습니다.",
        "err.refresh_required": "Refresh 토큰이 필요합니다.",
        "err.user_not_found": "사용자를 찾을 수 없습니다.",
        "err.current_pw_wrong": "현재 패스워드가 올바르지 않습니다.",
        "err.decrypt_failed": "복호화 실패: 키가 올바르지 않거나 데이터가 손상되었습니다.",
        "err.backup_decrypt_failed": "백업 복호화 실패: 백업 패스워드가 올바르지 않거나 파일이 손상되었습니다.",
        "err.key_not_found": "API 키를 찾을 수 없습니다.",
        "err.history_not_found": "해당 이력을 찾을 수 없습니다.",
        "err.rollback_failed": "롤백 불가: 현재 키로 복호화할 수 없습니다.",
        "err.backup_format": "백업 파일 형식이 올바르지 않습니다.",
        "err.backup_version": "지원하지 않는 백업 버전입니다.",
        "err.file_not_found": ".env 파일을 찾을 수 없습니다.",
        "err.entry_not_found": "엔트리를 찾을 수 없습니다.",
        "err.file_missing_disk": "파일이 존재하지 않습니다: {path}",
        "err.parent_missing": "상위 디렉토리가 없습니다: {path}",
        "err.key_exists": "이미 존재하는 키입니다: {key}",
        "err.snapshot_not_found": "스냅샷을 찾을 수 없습니다.",
        "err.restore_failed": "복원 불가: 복호화할 수 없습니다.",
        "err.diff_failed": "diff 불가: 복호화할 수 없습니다.",
        "err.dir_not_found": "디렉토리가 존재하지 않습니다: {path}",
        # 성공 메시지
        "msg.setup_done": "설정 완료. 사용자 '{username}' 생성됨.",
        "msg.logout_done": "로그아웃 완료. Vault 잠금.",
        "msg.pw_changed": "로그인 패스워드가 변경되었습니다.",
        "msg.master_changed": "마스터 패스워드 변경 및 전체 재암호화 완료.",
        "msg.key_deleted": "키 '{name}' 삭제 완료.",
        "msg.import_done": "복원 완료: {imported}건 반영, {skipped}건 건너뜀.",
        "msg.file_unregistered": "'{name}' 등록 해제 완료. 디스크 파일은 삭제되지 않았습니다.",
        "msg.sync_pull": "pull 완료: 추가 {added}, 갱신 {updated}, 유지 {kept}.",
        "msg.sync_push": "push 완료: {count}개 항목을 {path} 에 기록했습니다.",
        "msg.entry_deleted": "엔트리 '{key}' 삭제 완료.",
        "msg.snapshot_restored": "스냅샷 #{id} 복원 완료 ({count}개 항목).",
        "msg.link_added": "'{key}' ↔ '{name}' 연결됨.",
        "msg.link_removed": "연결이 해제되었습니다.",
        # 키 테스트 / 사용량
        "test.ok": "정상 응답 (HTTP {code}). 키가 유효합니다.",
        "test.auth_fail": "인증 실패 (HTTP {code}). 키가 유효하지 않거나 권한이 없습니다.",
        "test.rate_limited": "키는 유효하나 요청이 제한됨 (HTTP {code}).",
        "test.unexpected": "예상치 못한 응답 (HTTP {code}).",
        "test.network_err": "네트워크 오류: {err}",
        "test.unsupported": "지원하지 않는 서비스입니다: {service}",
        "test.detect_fail": "서비스를 자동 감지하지 못했습니다. service 필드를 지정하세요.",
        "test.detect_fail_short": "서비스를 자동 감지하지 못했습니다.",
        "usage.unsupported": "이 서비스는 사용량 조회를 지원하지 않습니다.",
        "usage.ok": "사용량 조회 성공.",
        "usage.network_err": "네트워크 오류: {err}",
        "usage.failed": "사용량 조회 실패 (HTTP {code}).",
    },
    "en": {
        "err.internal": "An internal server error occurred.",
        "err.wrong_credentials": "Incorrect username or password.",
        "err.account_locked": "Account locked. Try again in {minutes} min.",
        "err.too_many_attempts": "Too many login attempts ({max}). Try again in {lockout} min.",
        "err.bad_master": "Incorrect master password.",
        "err.vault_not_init": "The vault is not initialized. Complete setup first.",
        "err.vault_already_init": "The vault is already initialized.",
        "err.vault_locked": "The vault is locked. Please log in again.",
        "err.setup_done": "Setup is already complete.",
        "err.invalid_token": "Invalid token.",
        "err.logged_out_token": "This token has already been logged out.",
        "err.token_type": "Invalid token type.",
        "err.refresh_required": "A refresh token is required.",
        "err.user_not_found": "User not found.",
        "err.current_pw_wrong": "The current password is incorrect.",
        "err.decrypt_failed": "Decryption failed: wrong key or corrupted data.",
        "err.backup_decrypt_failed": "Backup decryption failed: wrong backup password or corrupted file.",
        "err.key_not_found": "API key not found.",
        "err.history_not_found": "That history entry was not found.",
        "err.rollback_failed": "Cannot roll back: cannot decrypt with the current key.",
        "err.backup_format": "The backup file format is invalid.",
        "err.backup_version": "Unsupported backup version.",
        "err.file_not_found": ".env file not found.",
        "err.entry_not_found": "Entry not found.",
        "err.file_missing_disk": "File does not exist: {path}",
        "err.parent_missing": "Parent directory does not exist: {path}",
        "err.key_exists": "Key already exists: {key}",
        "err.snapshot_not_found": "Snapshot not found.",
        "err.restore_failed": "Cannot restore: decryption failed.",
        "err.diff_failed": "Cannot diff: decryption failed.",
        "err.dir_not_found": "Directory does not exist: {path}",
        "msg.setup_done": "Setup complete. User '{username}' created.",
        "msg.logout_done": "Logged out. Vault locked.",
        "msg.pw_changed": "Login password changed.",
        "msg.master_changed": "Master password changed and everything re-encrypted.",
        "msg.key_deleted": "Key '{name}' deleted.",
        "msg.import_done": "Restore complete: {imported} applied, {skipped} skipped.",
        "msg.file_unregistered": "'{name}' unregistered. The disk file was not deleted.",
        "msg.sync_pull": "Pull complete: added {added}, updated {updated}, kept {kept}.",
        "msg.sync_push": "Push complete: wrote {count} entries to {path}.",
        "msg.entry_deleted": "Entry '{key}' deleted.",
        "msg.snapshot_restored": "Snapshot #{id} restored ({count} entries).",
        "msg.link_added": "Linked '{key}' ↔ '{name}'.",
        "msg.link_removed": "Link removed.",
        "test.ok": "OK response (HTTP {code}). The key is valid.",
        "test.auth_fail": "Auth failed (HTTP {code}). The key is invalid or lacks permission.",
        "test.rate_limited": "Key is valid but requests are rate-limited (HTTP {code}).",
        "test.unexpected": "Unexpected response (HTTP {code}).",
        "test.network_err": "Network error: {err}",
        "test.unsupported": "Unsupported service: {service}",
        "test.detect_fail": "Could not auto-detect the service. Specify the service field.",
        "test.detect_fail_short": "Could not auto-detect the service.",
        "usage.unsupported": "This service does not support usage lookup.",
        "usage.ok": "Usage retrieved successfully.",
        "usage.network_err": "Network error: {err}",
        "usage.failed": "Usage lookup failed (HTTP {code}).",
    },
    "ja": {
        "err.internal": "内部サーバーエラーが発生しました。",
        "err.wrong_credentials": "ユーザー名またはパスワードが正しくありません。",
        "err.account_locked": "アカウントがロックされています。{minutes}分後に再試行してください。",
        "err.too_many_attempts": "ログイン試行回数が{max}回を超えました。{lockout}分後に再試行してください。",
        "err.bad_master": "マスターパスワードが正しくありません。",
        "err.vault_not_init": "Vault が初期化されていません。先に設定を完了してください。",
        "err.vault_already_init": "Vault は既に初期化されています。",
        "err.vault_locked": "Vault がロックされています。再度ログインしてください。",
        "err.setup_done": "設定は既に完了しています。",
        "err.invalid_token": "無効なトークンです。",
        "err.logged_out_token": "このトークンは既にログアウト済みです。",
        "err.token_type": "トークンの種類が正しくありません。",
        "err.refresh_required": "リフレッシュトークンが必要です。",
        "err.user_not_found": "ユーザーが見つかりません。",
        "err.current_pw_wrong": "現在のパスワードが正しくありません。",
        "err.decrypt_failed": "復号に失敗しました: キーが正しくないかデータが破損しています。",
        "err.backup_decrypt_failed": "バックアップの復号に失敗しました: バックアップパスワードが誤っているかファイルが破損しています。",
        "err.key_not_found": "API キーが見つかりません。",
        "err.history_not_found": "該当する履歴が見つかりません。",
        "err.rollback_failed": "ロールバック不可: 現在のキーで復号できません。",
        "err.backup_format": "バックアップファイルの形式が正しくありません。",
        "err.backup_version": "サポートされていないバックアップバージョンです。",
        "err.file_not_found": ".env ファイルが見つかりません。",
        "err.entry_not_found": "エントリが見つかりません。",
        "err.file_missing_disk": "ファイルが存在しません: {path}",
        "err.parent_missing": "親ディレクトリが存在しません: {path}",
        "err.key_exists": "既に存在するキーです: {key}",
        "err.snapshot_not_found": "スナップショットが見つかりません。",
        "err.restore_failed": "復元不可: 復号できません。",
        "err.diff_failed": "差分不可: 復号できません。",
        "err.dir_not_found": "ディレクトリが存在しません: {path}",
        "msg.setup_done": "設定完了。ユーザー「{username}」を作成しました。",
        "msg.logout_done": "ログアウト完了。Vault をロックしました。",
        "msg.pw_changed": "ログインパスワードを変更しました。",
        "msg.master_changed": "マスターパスワードを変更し、全て再暗号化しました。",
        "msg.key_deleted": "キー「{name}」を削除しました。",
        "msg.import_done": "復元完了: {imported}件反映、{skipped}件スキップ。",
        "msg.file_unregistered": "「{name}」の登録を解除しました。ディスク上のファイルは削除されていません。",
        "msg.sync_pull": "pull 完了: 追加 {added}、更新 {updated}、維持 {kept}。",
        "msg.sync_push": "push 完了: {count} 件を {path} に書き込みました。",
        "msg.entry_deleted": "エントリ「{key}」を削除しました。",
        "msg.snapshot_restored": "スナップショット #{id} を復元しました（{count} 件）。",
        "msg.link_added": "「{key}」↔「{name}」をリンクしました。",
        "msg.link_removed": "リンクを解除しました。",
        "test.ok": "正常応答 (HTTP {code})。キーは有効です。",
        "test.auth_fail": "認証失敗 (HTTP {code})。キーが無効か権限がありません。",
        "test.rate_limited": "キーは有効ですがリクエストが制限されています (HTTP {code})。",
        "test.unexpected": "予期しない応答 (HTTP {code})。",
        "test.network_err": "ネットワークエラー: {err}",
        "test.unsupported": "サポートされていないサービスです: {service}",
        "test.detect_fail": "サービスを自動判定できませんでした。service フィールドを指定してください。",
        "test.detect_fail_short": "サービスを自動判定できませんでした。",
        "usage.unsupported": "このサービスは使用量の取得に対応していません。",
        "usage.ok": "使用量を取得しました。",
        "usage.network_err": "ネットワークエラー: {err}",
        "usage.failed": "使用量の取得に失敗しました (HTTP {code})。",
    },
    "zh": {
        "err.internal": "发生内部服务器错误。",
        "err.wrong_credentials": "用户名或密码不正确。",
        "err.account_locked": "账户已锁定。请在 {minutes} 分钟后重试。",
        "err.too_many_attempts": "登录尝试次数超过 {max} 次。请在 {lockout} 分钟后重试。",
        "err.bad_master": "主密码不正确。",
        "err.vault_not_init": "保险库尚未初始化。请先完成设置。",
        "err.vault_already_init": "保险库已初始化。",
        "err.vault_locked": "保险库已锁定。请重新登录。",
        "err.setup_done": "已完成设置。",
        "err.invalid_token": "无效的令牌。",
        "err.logged_out_token": "该令牌已退出登录。",
        "err.token_type": "令牌类型不正确。",
        "err.refresh_required": "需要刷新令牌。",
        "err.user_not_found": "未找到用户。",
        "err.current_pw_wrong": "当前密码不正确。",
        "err.decrypt_failed": "解密失败：密钥不正确或数据已损坏。",
        "err.backup_decrypt_failed": "备份解密失败：备份密码不正确或文件已损坏。",
        "err.key_not_found": "未找到 API 密钥。",
        "err.history_not_found": "未找到该历史记录。",
        "err.rollback_failed": "无法回滚：无法用当前密钥解密。",
        "err.backup_format": "备份文件格式无效。",
        "err.backup_version": "不支持的备份版本。",
        "err.file_not_found": "未找到 .env 文件。",
        "err.entry_not_found": "未找到条目。",
        "err.file_missing_disk": "文件不存在: {path}",
        "err.parent_missing": "上级目录不存在: {path}",
        "err.key_exists": "键已存在: {key}",
        "err.snapshot_not_found": "未找到快照。",
        "err.restore_failed": "无法恢复：解密失败。",
        "err.diff_failed": "无法比较：解密失败。",
        "err.dir_not_found": "目录不存在: {path}",
        "msg.setup_done": "设置完成。已创建用户“{username}”。",
        "msg.logout_done": "已退出登录。保险库已锁定。",
        "msg.pw_changed": "已修改登录密码。",
        "msg.master_changed": "已修改主密码并完成全部重新加密。",
        "msg.key_deleted": "已删除密钥“{name}”。",
        "msg.import_done": "恢复完成：应用 {imported} 项，跳过 {skipped} 项。",
        "msg.file_unregistered": "已取消注册“{name}”。磁盘上的文件未删除。",
        "msg.sync_pull": "pull 完成：新增 {added}，更新 {updated}，保留 {kept}。",
        "msg.sync_push": "push 完成：已将 {count} 项写入 {path}。",
        "msg.entry_deleted": "已删除条目“{key}”。",
        "msg.snapshot_restored": "已恢复快照 #{id}（{count} 项）。",
        "msg.link_added": "已关联“{key}”↔“{name}”。",
        "msg.link_removed": "已取消关联。",
        "test.ok": "正常响应 (HTTP {code})。密钥有效。",
        "test.auth_fail": "认证失败 (HTTP {code})。密钥无效或无权限。",
        "test.rate_limited": "密钥有效，但请求被限流 (HTTP {code})。",
        "test.unexpected": "意外的响应 (HTTP {code})。",
        "test.network_err": "网络错误: {err}",
        "test.unsupported": "不支持的服务: {service}",
        "test.detect_fail": "无法自动识别服务。请指定 service 字段。",
        "test.detect_fail_short": "无法自动识别服务。",
        "usage.unsupported": "该服务不支持用量查询。",
        "usage.ok": "用量查询成功。",
        "usage.network_err": "网络错误: {err}",
        "usage.failed": "用量查询失败 (HTTP {code})。",
    },
}


# ──────────────────────────────────────────────────────────────
# 로케일 결정 / 번역
# ──────────────────────────────────────────────────────────────

def pick_locale(x_lang: str = None, accept_language: str = None) -> str:
    """X-Lang 우선, 없으면 Accept-Language, 둘 다 없으면 기본."""
    if x_lang:
        code = x_lang.strip().lower()[:2]
        if code in SUPPORTED:
            return code
    if accept_language:
        # "ja,en-US;q=0.9" → 첫 항목의 언어 코드
        first = accept_language.split(",")[0].strip().lower()[:2]
        if first in SUPPORTED:
            return first
    return DEFAULT_LOCALE


def translate(message_key: str, locale: str, **params) -> str:
    table = MESSAGES.get(locale, MESSAGES[DEFAULT_LOCALE])
    template = (
        table.get(message_key)
        or MESSAGES[DEFAULT_LOCALE].get(message_key)
        or message_key
    )
    if params:
        try:
            return template.format(**params)
        except (KeyError, IndexError, ValueError):
            return template
    return template


def locale_from_request(request: Request) -> str:
    return pick_locale(
        request.headers.get("x-lang"),
        request.headers.get("accept-language"),
    )


# ──────────────────────────────────────────────────────────────
# 예외 / 의존성
# ──────────────────────────────────────────────────────────────

class AppError(Exception):
    """번역 키를 담는 애플리케이션 예외. 전역 핸들러가 로케일로 번역."""

    def __init__(self, message_key: str, status_code: int = 400, **params):
        self.key = message_key
        self.status_code = status_code
        self.params = params
        super().__init__(message_key)


def get_translator(request: Request):
    """엔드포인트에서 성공 메시지 번역용. t = Depends(get_translator)"""
    locale = locale_from_request(request)

    def t(message_key: str, **params) -> str:
        return translate(message_key, locale, **params)

    t.locale = locale
    return t
