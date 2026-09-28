# Deployment — free-tier stack (Supabase + Render + Cloudflare)

Three free building blocks for a real, non-Docker deployment:

| Component | Provider | Free tier note |
|-----------|----------|----------------|
| PostgreSQL | Supabase | 500 MB database, 5 GB egress/month. **Idle projects auto-suspend after 1 week of inactivity** — a free Supabase DB is *not* guaranteed always-on. Upgrade to Pro (~US$25/mo) when the business grows. |
| Backend API | Render (Web Service) | 750 instance-hours/month ≈ ~31 days if sleep is disabled; **free tier sleeps after 15 min of idle** → first request after sleep takes a few seconds. Upgrade to ECO (~US$7/mo) for always-on indoors. |
| Frontend | Cloudflare Pages | Unlimited static requests/bandwidth — the Vite `dist/` build fits comfortably. |

Render and Cloudflare may change free-tier policy anytime; re-read the current terms before relying on them.

## Why asyncpg needs the *direct* Supabase connection

The backend drives Postgres with **asyncpg, which uses prepared statements**.
Supabase's transaction pooler (port **6543**) rejects them, so you must use the
**direct connection (port 5432)** string and add `sslmode=require`. Prepared
statements, `SELECT ... FOR UPDATE`, and the `txn_no_seq`/`refund_no_seq`
sequences all work fine on the direct connection.

## 1. Database — Supabase

1. Create a project (region closest to your users).
2. Dashboard → Project Settings → Database → **Connection string** tab.
   - Choose **General → Direct connection**.
   - Copy the URI and rewrite it into the asyncpg form:
     ```
     postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
     ```
     ⚠️ Port **5432** (direct), *not* 6543 (the pgbouncer transaction pooler).
3. Use this string where Render's `DATABASE_URL` expects it. Never commit it.

## 2. Backend — Render (Web Service)

1. **New Web Service** → connect the GitHub repo → root directory `backend`, runtime **Docker** (uses `backend/Dockerfile`).
2. On boot the container runs `alembic upgrade head && uvicorn ...` — migrations are applied automatically.
3. Environment:

   | Variable | Value |
   |----------|-------|
   | `APP_ENV` | `production` |
   | `DATABASE_URL` | Supabase direct URL (above) |
   | `JWT_SECRET` | long random string (≥32 chars) |
   | `CORS_ORIGINS` | `["https://<your-site>.pages.dev"]` |
   | `TAX_RATE_PERCENT` | `8.00` |
   | `LOGIN_RATE_LIMIT` | `10/minute` |
   | `EXPOSE_DOCS` | `false` |

4. Health check path: `/api/v1/health`. Free tier sleeps after 15 min idle.

## 3. Frontend — Cloudflare

### Option A: Workers (default, already configured)

A `wrangler.jsonc` at the repo root deploys the SPA as a Worker with static
assets (`frontend/dist`) plus a tiny proxy (`frontend/scripts/worker.js`) that
forwards `/api/*` to the backend. SPA fallback is handled by
`not_found_handling: "single-page-application"`.

- Preview: `npx wrangler preview` (also what the Cloudflare dashboard runs) or `npm run cf:preview`.
- Live: `npm run cf:deploy` → `https://pitstop-pos.diniemuzaffar.workers.dev`.
- Point the proxy at the backend by setting the **`API_BASE`** binding:
  - locally: `npx wrangler deploy --var API_BASE:https://<your-service>.onrender.com`
  - or edit `vars` in `wrangler.jsonc` (placeholder must be replaced once Render is live).

### Option B: Pages

1. Create a Pages project → connect repo → **framework: Vite**, root `frontend`, build command `npm run build`, output directory `dist`.
2. The SPA calls relative `/api/...` paths; `frontend/public/_redirects` is copied into the build and forwards them to Render:
   ```
   /api/*  https://<your-service>.onrender.com/api/:splat  200
   ```
   **Edit the placeholder host after your Render service is live.**
3. Deploy. Visit `https://<your-subdomain>.pages.dev`.

> Either way: **until the backend is deployed and the proxy/`_redirects` host
> points at it, the online site's API calls fail** — the shell loads, login
> does not. That is expected while the API only runs on your laptop.

## One-time data setup (from your machine, after merging)

```powershell
cd backend
$env:DATABASE_URL = "postgresql+asyncpg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres?ssl=require"
uv run alembic upgrade head
uv run python -m app.seed       # demo users, 36 products, ~360 transactions
```

## Checklist before going live

- [ ] Strong `JWT_SECRET` set on Render, never in code.
- [ ] `CORS_ORIGINS` pinned to the real Pages domain.
- [ ] `_redirects` host edited to the actual Render URL.
- [ ] `EXPOSE_DOCS=false`.
- [ ] Demo credentials (`admin/Admin@2026`, etc.) changed or users replaced.
- [ ] Health check `/health` registered (Render restarts on failure).
- [ ] Supabase → Project Settings → Database → enable **point-in-time restore / daily backups** if available on your plan.

## Upgrade path (when "free" stops being enough)

- Render free sleeps → **ECO $7/mo** (always-on). Backend behind UptimeRobot pings is a stopgap that burns roughly half of the free 750 h.
- Supabase free suspends after 7 idle days → **Pro $25/mo** (no suspend, full backups).
- Cloudflare Pages free tier is effectively permanent for a POS dashboard — keep it.

## Non-negotiable honesty note

"Free" trial Postgres suspends, and free compute sleeps. This stack is an excellent **zero-cost start**, not a permanent production guarantee — budget for paid tiers from day one of real, daily use.