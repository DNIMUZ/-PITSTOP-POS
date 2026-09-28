# PITSTOP POS

A production-style, full-stack **Point of Sale** built with FastAPI + PostgreSQL on the backend and React + Vite + Tailwind on the frontend. Real database persistence, atomic / concurrency-safe checkout, JWT + role-based access control, and a Python test suite that asserts exact-cent money math.

Designed for free-tier deployment (see [docs/DEPLOYMENT_FREE_TIER.md](docs/DEPLOYMENT_FREE_TIER.md)) and day-to-day local POS use on Windows.

---

## Stack

| Layer      | Tech |
|------------|------|
| Backend    | Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, asyncpg, slowapi, Pydantic v2, uv |
| Frontend   | React 19, TypeScript, Vite 5, Tailwind CSS 4, TanStack Query, react-router |
| Database   | PostgreSQL 16 (single-writer; `SELECT ... FOR UPDATE` for safe concurrency) |
| Quality    | pytest (37 tests), ruff, `tsc --strict`, GitHub Actions |

## Features

- **Atomic checkout** — sale + stock movement + payment commit in one DB transaction; concurrent last-unit purchases are serialized and fail cleanly with a 409.
- **Server-side money** — `NUMERIC(12,2)` + `Decimal` end to end; subtotal / 8% SST / discount handling computed by the API and trusted over any client.
- **RBAC** — `admin`, `manager`, `cashier` with route-level guards (products, inventory adjustments, refunds require manager+; cashier sees only their own transactions).
- **Refunds** — full/partial, stock restocked, refunds scale by the actually-paid amount (tax + discount adjusted).
- **POS UX** — barcode scanning (F2 to focus), product lookup, cart, payment methods (cash / card / QR / eWallet), tender + change, printable receipt, low-stock hints.
- **Dashboard** — revenue today, orders, average order value, items sold, last-7-days revenue, top products, low stock.
- **Seed** — 3 users, 6 categories, 36 products (quantity priced), and ~360 historical transactions for instant demo data.

## Repository layout

```
pitstop-pos/
├── backend/
│   ├── app/            # models, schemas, repositories, services, routers, db, core, seed
│   ├── alembic/        # migrations (4 applied to dev + test DBs)
│   ├── tests/          # 37 tests: health, auth, products, transactions, refunds, rbac, analytics
│   ├── pyproject.toml  # uv project: deps, pytest config, ruff config
│   └── Dockerfile
├── frontend/
│   ├── src/            # types, api client, auth context, UI primitives, pages
│   └── Dockerfile      # Vite build → nginx static + SPA fallback
├── infra/              # docker-compose (Postgres + backend + frontend)
├── .github/workflows/  # backend (lint + 37 tests on GitHub Postgres) and frontend (npm build)
└── docs/
```

## Local development (Windows)

Prerequisites: **PostgreSQL 16** running locally, **Python 3.11**, **uv**, **Node 22+**.

### 1. Backend

```powershell
# create database + role once
psql -U postgres -c "CREATE ROLE pitstop WITH LOGIN PASSWORD 'pitstop_dev_password';"
psql -U postgres -c "CREATE DATABASE pitstop_dev OWNER pitstop;"
psql -U postgres -c "CREATE DATABASE pitstop_test OWNER pitstop;"

cd backend
Copy-Item .env.example .env        # then edit DATABASE_URL/JWT_SECRET as needed
uv sync
uv run alembic upgrade head
uv run python -m app.seed          # demo users, products, transactions
uv run uvicorn app.main:app --reload
```

API docs: <http://127.0.0.1:8000/docs>.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

### Seed credentials

| Role    | Username | Password     |
|---------|----------|--------------|
| admin   | `admin`  | `Admin@2026` |
| manager | `manager`| `Manager@2026` |
| cashier | `cashier`| `Cashier@2026` |

Barcodes are `PPS000001`–`PPS000036` (same as `APX-101`... `KID-609` SKUs), so the POS scan box accepts either.

### 3. Tests

```powershell
cd backend
uv run pytest -q      # expects a reachable pitstop_test DB (runs its own migrations)
uv run ruff check .
```

## Docker

```powershell
cd infra
Copy-Item .env.example .env   # set JWT_SECRET
docker compose up --build
```

Frontend: http://localhost:8080 · API: http://localhost:8000 · Docs: http://localhost:8000/docs

## Deployment

Free-tier guide with a real database provider (Neon) and a note on free Postgres expiry: **[docs/DEPLOYMENT_FREE_TIER.md](docs/DEPLOYMENT_FREE_TIER.md)**.

In production always set a strong `JWT_SECRET`, pin `CORS_ORIGINS` to your frontend domain, and set `EXPOSE_DOCS=false`.

## Version log

| Version | Date       | Summary |
|---------|------------|---------|
| 1.0.0   | 2026-09-29 | Full backend (models, migrations, RBAC, atomic POS, refunds, analytics, seed) + 37 passing tests + React POS frontend (login, dashboard, POS, products, inventory, transactions, refunds). |