<div align="center">

# 🔐 ENV Vault

**A local-first console for managing `.env` files and API keys — encrypted, searchable, and fully offline.**

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![AES-256-GCM](https://img.shields.io/badge/Encryption-AES--256--GCM-2ea44f)

**English** · [한국어](README.ko.md) · [日本語](README.ja.md)

</div>

---

Your secrets never leave your machine. ENV Vault binds to `127.0.0.1` only, encrypts every value with **AES-256-GCM**, and derives its key from a master password you alone know — nothing sensitive is ever stored in plaintext or sent to a third party.

---

## Features

### 🔒 Security & Encryption
| | |
|---|---|
| **Encryption** | AES-256-GCM for every API key and `.env` value |
| **Key derivation** | PBKDF2-SHA256 (600,000 iterations) from your master password |
| **At rest** | Only ciphertext in SQLite — master password is never stored |
| **Auto-lock** | Vault key kept in memory only, auto-locks after inactivity |
| **Hardening** | bcrypt (cost 12), JWT access/refresh + JTI denylist, login rate-limit & lockout, strict CSP |

### 🔑 API Keys
- Create, edit, delete with **change history** and one-click **rollback**
- Reveal / copy with a **30-second auto-clearing clipboard**
- **Live key testing** against OpenAI, Anthropic, GitHub, Google, Stripe (status badges)
- Encrypted **backup / restore** (`.envbackup`) with an independent backup password
- Expiry tracking with **D-7 browser notifications**

### 📄 .env Files
- Register on-disk `.env` files and **sync** disk ↔ DB (pull / push)
- Per-entry CRUD with comment preservation
- **Snapshots**, **diff**, and **restore** to any point in time
- **Code-usage scan** — grep your project for where each key is used
- Link API keys to `.env` entries (M:N)

### 🎨 UI & Language
- Real brand logos, auto-detected from the key format
- Dark / light theme, fully responsive
- **4 languages** — English (default) · 한국어 · 日本語 · 中文 (UI **and** server messages)

---

## Getting Started

### One-click

```bash
bash start.sh
```

This generates a self-signed SSL certificate, sets up the Python virtualenv, builds the frontend, and starts the server. Then open **https://127.0.0.1:8443**.

### Manual

**Backend**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # https://127.0.0.1:8443
```

**Frontend** (dev server with hot reload)
```bash
cd frontend
npm install
npm run dev               # http://127.0.0.1:5173  (proxies /api → backend)
```

On first visit you'll be guided through **Setup** — create your admin account and master password.

> ⚠️ The master password cannot be recovered. If you lose it, encrypted values cannot be decrypted.

---

## Security Architecture

```
[Browser] ──HTTPS──▶ [FastAPI @ 127.0.0.1:8443]
                            │
            ┌───────────────┼───────────────┐
       [JWT Auth]    [AES-256-GCM]     [bcrypt 12]
            │              │                │
       sessions      value encryption   password hash
                            │
                [SQLite vault.db — ciphertext only]
                            │
                 [.vault_salt + .vault_verify]
                  master PW → key derivation
```

- `127.0.0.1`-only binding + TrustedHost middleware (no external exposure)
- Master password → PBKDF2-SHA256 (600k) → AES-256 key, held in memory only
- JWT access (15 min) + refresh (7 days) with rotation and a revocation denylist
- Login rate-limiting (slowapi) and account lockout after repeated failures
- Strict security headers including a Content-Security-Policy

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest                    # crypto, parser, auth, keys, env files, i18n, rate-limit
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python · FastAPI · Uvicorn |
| Database | SQLite (SQLAlchemy 2.0, WAL) |
| Crypto | `cryptography` — AES-256-GCM · PBKDF2 |
| Auth | bcrypt · python-jose (JWT) · slowapi |
| Frontend | React 18 · Vite 5 · Tailwind CSS 3 |
| i18n | Custom dictionary (UI + server messages) |

---

## Project Structure

```
env-vault/
├── main.py                # FastAPI app, middleware, exception handlers
├── config.py              # settings, paths, JWT/security constants
├── crypto.py              # AES-256-GCM + PBKDF2 key derivation
├── auth.py / auth_router.py
├── keys_router.py         # API key CRUD, history, backup/restore
├── envfiles_router.py     # .env files, sync, snapshots, diff, scan
├── test_router.py         # live key testing
├── i18n.py                # backend message translations (en/ko/ja/zh)
├── models.py / schemas.py / database.py
├── tests/                 # pytest suite
└── frontend/
    └── src/
        ├── pages/         # Login, Setup, Dashboard, ApiKeys, EnvFiles, Settings
        ├── components/    # Layout, MaskedValue, DiffViewer, Icon, ...
        ├── hooks/         # useAuth, useVault, useTheme
        └── i18n.jsx       # frontend translations (en/ko/ja/zh)
```
