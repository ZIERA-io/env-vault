<div align="center">

# 🔐 ENV Vault

**`.env` ファイルと API キーを暗号化して管理するローカル専用コンソール — 検索可能で完全オフライン。**

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![AES-256-GCM](https://img.shields.io/badge/Encryption-AES--256--GCM-2ea44f)

[English](README.md) · [한국어](README.ko.md) · **日本語**

</div>

---

シークレットがマシンの外に出ることはありません。ENV Vault は `127.0.0.1` のみにバインドし、すべての値を **AES-256-GCM** で暗号化、鍵はあなただけが知るマスターパスワードから導出されます — 機密値が平文で保存されたり第三者へ送信されることはありません。

---

## 主な機能

### 🔒 セキュリティと暗号化
| | |
|---|---|
| **暗号化** | すべての API キー・`.env` 値に AES-256-GCM |
| **鍵導出** | マスターパスワード → PBKDF2-SHA256（600,000 回） |
| **保存形態** | SQLite には暗号文のみ — マスターパスワードは保存しない |
| **自動ロック** | Vault 鍵はメモリ上のみ、無操作で自動ロック |
| **堅牢化** | bcrypt（cost 12）、JWT access/refresh + JTI 失効リスト、ログイン制限・ロック、厳格な CSP |

### 🔑 API キー
- 作成・編集・削除 +**変更履歴**とワンクリック**ロールバック**
- 表示 / コピー時に**30 秒で自動クリアされるクリップボード**
- OpenAI・Anthropic・GitHub・Google・Stripe への**リアルタイムキーテスト**（ステータスバッジ）
- 独立したバックアップパスワードによる暗号化**バックアップ / 復元**（`.envbackup`）
- 有効期限の追跡 +**期限 7 日前のブラウザ通知**

### 📄 .env ファイル
- ディスク上の `.env` を登録してディスク ↔ DB **同期**（pull / push）
- コメントを保持するエントリ CRUD
- **スナップショット**、**差分**、任意時点への**復元**
- **コード使用箇所スキャン** — プロジェクト内で各キーが使われている場所を grep
- API キー ↔ `.env` エントリのリンク（M:N）

### 🎨 UI と言語
- キー形式から自動判定される実際のブランドロゴ
- ダーク / ライトテーマ、完全レスポンシブ
- **4 言語** — English（デフォルト）· 한국어 · 日本語 · 中文（UI **および**サーバーメッセージ）

---

## はじめに

### ワンクリック

```bash
bash start.sh
```

自己署名 SSL 証明書の生成、Python 仮想環境の構築、フロントエンドのビルド、サーバー起動までを一括で行います。その後 **https://127.0.0.1:8443** を開いてください。

### 手動

**バックエンド**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # https://127.0.0.1:8443
```

**フロントエンド**（ホットリロード開発サーバー）
```bash
cd frontend
npm install
npm run dev               # http://127.0.0.1:5173  (/api → バックエンドへプロキシ)
```

初回アクセス時に**セットアップ**画面で管理者アカウントとマスターパスワードを作成します。

> ⚠️ マスターパスワードは復元できません。紛失すると暗号化された値を復号できません。

---

## セキュリティアーキテクチャ

```
[ブラウザ] ──HTTPS──▶ [FastAPI @ 127.0.0.1:8443]
                            │
            ┌───────────────┼───────────────┐
       [JWT 認証]    [AES-256-GCM]     [bcrypt 12]
            │              │                │
       セッション管理   値の暗号化       パスワードハッシュ
                            │
                [SQLite vault.db — 暗号文のみ保存]
                            │
                 [.vault_salt + .vault_verify]
                  マスター PW → 鍵導出
```

- `127.0.0.1` 専用バインド + TrustedHost ミドルウェア（外部公開なし）
- マスターパスワード → PBKDF2-SHA256（600k）→ AES-256 鍵、メモリ上のみで保持
- JWT access（15 分）+ refresh（7 日）、ローテーションと失効リスト
- ログインのレート制限（slowapi）と連続失敗時のアカウントロック
- CSP を含む厳格なセキュリティヘッダー

---

## テスト

```bash
pip install -r requirements-dev.txt
pytest                    # crypto, パーサ, 認証, キー, .env, i18n, レート制限
```

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| バックエンド | Python · FastAPI · Uvicorn |
| データベース | SQLite (SQLAlchemy 2.0, WAL) |
| 暗号化 | `cryptography` — AES-256-GCM · PBKDF2 |
| 認証 | bcrypt · python-jose (JWT) · slowapi |
| フロントエンド | React 18 · Vite 5 · Tailwind CSS 3 |
| i18n | 独自辞書（UI + サーバーメッセージ） |

---

## プロジェクト構成

```
env-vault/
├── main.py                # FastAPI アプリ、ミドルウェア、例外ハンドラ
├── config.py              # 設定、パス、JWT/セキュリティ定数
├── crypto.py              # AES-256-GCM + PBKDF2 鍵導出
├── auth.py / auth_router.py
├── keys_router.py         # API キー CRUD、履歴、バックアップ/復元
├── envfiles_router.py     # .env ファイル、同期、スナップショット、差分、スキャン
├── test_router.py         # リアルタイムキーテスト
├── i18n.py                # バックエンドメッセージ翻訳 (en/ko/ja/zh)
├── models.py / schemas.py / database.py
├── tests/                 # pytest スイート
└── frontend/
    └── src/
        ├── pages/         # Login, Setup, Dashboard, ApiKeys, EnvFiles, Settings
        ├── components/    # Layout, MaskedValue, DiffViewer, Icon, ...
        ├── hooks/         # useAuth, useVault, useTheme
        └── i18n.jsx       # フロントエンド翻訳 (en/ko/ja/zh)
```
