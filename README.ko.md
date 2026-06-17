<div align="center">

# 🔐 ENV Vault

**`.env` 파일과 API 키를 암호화해 관리하는 로컬 전용 콘솔 — 검색 가능하고 완전 오프라인.**

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![AES-256-GCM](https://img.shields.io/badge/Encryption-AES--256--GCM-2ea44f)

[English](README.md) · **한국어** · [日本語](README.ja.md)

</div>

---

비밀 값은 기기를 절대 벗어나지 않습니다. ENV Vault는 `127.0.0.1`에만 바인딩되고, 모든 값을 **AES-256-GCM**으로 암호화하며, 키는 오직 본인만 아는 마스터 패스워드에서 유도됩니다 — 민감한 값이 평문으로 저장되거나 제3자에게 전송되는 일은 없습니다.

---

## 주요 기능

### 🔒 보안 & 암호화
| | |
|---|---|
| **암호화** | 모든 API 키·`.env` 값에 AES-256-GCM 적용 |
| **키 유도** | 마스터 패스워드 → PBKDF2-SHA256 (600,000회 반복) |
| **저장 상태** | SQLite에는 암호문만 — 마스터 패스워드는 저장 안 함 |
| **자동 잠금** | Vault 키는 메모리에만 보관, 비활성 시 자동 잠금 |
| **보안 강화** | bcrypt(cost 12), JWT access/refresh + JTI 폐기목록, 로그인 속도제한·잠금, 엄격한 CSP |

### 🔑 API 키
- 생성·수정·삭제 + **변경 이력**과 원클릭 **롤백**
- 보기 / 복사 시 **30초 후 자동 초기화되는 클립보드**
- OpenAI·Anthropic·GitHub·Google·Stripe 대상 **실시간 키 테스트** (상태 배지)
- 독립 백업 패스워드로 암호화 **백업 / 복원** (`.envbackup`)
- 만료일 추적 + **D-7 브라우저 알림**

### 📄 .env 파일
- 디스크의 `.env` 파일 등록 후 디스크 ↔ DB **동기화** (pull / push)
- 주석을 보존하는 엔트리 CRUD
- **스냅샷**, **diff**, 임의 시점 **복원**
- **코드 사용처 스캔** — 프로젝트에서 각 키가 쓰인 곳을 grep
- API 키 ↔ `.env` 엔트리 연결 (M:N)

### 🎨 UI & 언어
- 키 형식으로 자동 감지되는 실제 브랜드 로고
- 다크 / 라이트 테마, 완전 반응형
- **4개 언어** — English(기본) · 한국어 · 日本語 · 中文 (UI **및** 서버 메시지)

---

## 시작하기

### 원클릭

```bash
bash start.sh
```

자체 서명 SSL 인증서 생성, 파이썬 가상환경 구성, 프론트엔드 빌드, 서버 실행까지 한 번에 처리합니다. 이후 **https://127.0.0.1:8443** 으로 접속하세요.

### 수동 실행

**백엔드**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # https://127.0.0.1:8443
```

**프론트엔드** (핫 리로드 개발 서버)
```bash
cd frontend
npm install
npm run dev               # http://127.0.0.1:5173  (/api → 백엔드 프록시)
```

최초 접속 시 **설정** 화면에서 관리자 계정과 마스터 패스워드를 만듭니다.

> ⚠️ 마스터 패스워드는 복구할 수 없습니다. 분실 시 암호화된 값을 복호화할 수 없습니다.

---

## 보안 아키텍처

```
[브라우저] ──HTTPS──▶ [FastAPI @ 127.0.0.1:8443]
                            │
            ┌───────────────┼───────────────┐
       [JWT 인증]    [AES-256-GCM]     [bcrypt 12]
            │              │                │
        세션 관리      값 암호화        비밀번호 해시
                            │
                [SQLite vault.db — 암호문만 저장]
                            │
                 [.vault_salt + .vault_verify]
                  마스터 PW → 키 유도
```

- `127.0.0.1` 전용 바인딩 + TrustedHost 미들웨어 (외부 노출 차단)
- 마스터 패스워드 → PBKDF2-SHA256(600k) → AES-256 키, 메모리에만 유지
- JWT access(15분) + refresh(7일), 회전 및 폐기목록 적용
- 로그인 속도 제한(slowapi)과 반복 실패 시 계정 잠금
- CSP 포함 엄격한 보안 헤더

---

## 테스트

```bash
pip install -r requirements-dev.txt
pytest                    # crypto, 파서, 인증, 키, .env, i18n, 속도제한
```

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| 백엔드 | Python · FastAPI · Uvicorn |
| 데이터베이스 | SQLite (SQLAlchemy 2.0, WAL) |
| 암호화 | `cryptography` — AES-256-GCM · PBKDF2 |
| 인증 | bcrypt · python-jose (JWT) · slowapi |
| 프론트엔드 | React 18 · Vite 5 · Tailwind CSS 3 |
| i18n | 자체 사전 (UI + 서버 메시지) |

---

## 프로젝트 구조

```
env-vault/
├── main.py                # FastAPI 앱, 미들웨어, 예외 핸들러
├── config.py              # 설정, 경로, JWT/보안 상수
├── crypto.py              # AES-256-GCM + PBKDF2 키 유도
├── auth.py / auth_router.py
├── keys_router.py         # API 키 CRUD, 이력, 백업/복원
├── envfiles_router.py     # .env 파일, 동기화, 스냅샷, diff, 스캔
├── test_router.py         # 실시간 키 테스트
├── i18n.py                # 백엔드 메시지 번역 (en/ko/ja/zh)
├── models.py / schemas.py / database.py
├── tests/                 # pytest 스위트
└── frontend/
    └── src/
        ├── pages/         # Login, Setup, Dashboard, ApiKeys, EnvFiles, Settings
        ├── components/    # Layout, MaskedValue, DiffViewer, Icon, ...
        ├── hooks/         # useAuth, useVault, useTheme
        └── i18n.jsx       # 프론트엔드 번역 (en/ko/ja/zh)
```
