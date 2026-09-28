# Deployment — free-tier stack

Three rolling cloud components, all within free allowances, for a real (non-Docker) deployment:

| Component | Provider | Free tier note |
|-----------|----------|----------------|
| PostgreSQL | Neon | 0.5 GB / 200 compute-hours per month. **Free Postgres is not permanent** — idle branches/sleeping instances and compute-hour limits apply; a free trial DB typically pauses or expires. Plan for a paid tier ($19/mo for Neon Launch) when the business grows. |
| Backend API | Render (Web Service) | 750 instance-hours* / month covers ~31 days if you disable sleep (pauses on idle by default). Lock `JWT_SECRET`, `EXPOSE_DOCS=false`. |
| Frontend | Cloudflare Pages | Unlimited static bandwidth — the SPA build output fits comfortably. |

\* Render may change free-tier policy at any time; check the current terms before relying on it in production.

## 1. Database — Neon

1. Create a project (region near your users). Get the pooled connection string:
   `postgresql://<user>:<password>@<host>.pooler.supabase...` — for asyncpg use the **direct**, non-pooled URL:
   `postgresql://<user>:<password>@ep-<name>.eu-central-1.aws.neon.tech/pitstop_dev?sslmode=require`
2. Put this value into Render as `DATABASE_URL` (below). Do not commit real credentials.

## 2. Backend — Render (Web Service)

1. New Web Service → connect the GitHub repo → root directory `backend`, runtime **Docker** (uses `backend/Dockerfile`).
2. `uv sync` is not needed on Render — the container starts with `alembic upgrade head && uvicorn ...`, which applies migrations on boot.
3. Environment variables:

   | Variable | Value |
   |----------|-------|
   | `APP_ENV` | `production` |
   | `DATABASE_URL` | Neon direct URL (above), with `sslmode=require` |
   | `JWT_SECRET` | long random string (≥32 chars) |
   | `CORS_ORIGINS` | `["https://<your-cloudflare-subdomain>.pages.dev"]` |
   | `TAX_RATE_PERCENT` | `8.00` |
   | `LOGIN_RATE_LIMIT` | `10/minute` |
   | `EXPOSE_DOCS` | `false` |

4. Health check path: `/api/v1/health`. Free tier sleeps after 15 min of inactivity; first request after sleep takes a few seconds. Optional: `INFRASTRUCTURE` health probe on paid/always-on.

## 3. Frontend — Cloudflare Pages

1. Create Pages project → connect repo → **framework: Vite**, build command `npm run build` (run in `frontend`), output directory `dist`.
2. No server-side env needed; the SPA calls `/api/...` on the **same origin**, so set a proxy so `/api` reaches Render:
   - Add a `_redirects` in `frontend/public`:
     ```
     /api/*  https://<your-render-service>.onrender.com/api/:splat  200
     ```
     (Alternatively run the frontend and API behind a single domain/Caddy later.)
3. Deploy. Visit `https://<your-subdomain>.pages.dev`.

## Checklist before going live

- [ ] Strong `JWT_SECRET` generated and stored in provider env, never in code.
- [ ] `CORS_ORIGINS` pinned to the real frontend domain.
- [ ] `EXPOSE_DOCS=false`.
- [ ] Demo credentials (`admin/Admin@2026`, etc.) changed or users replaced.
- [ ] Backend health check registered (Render auto-restarts on failure).
- [ ] Backups: Neon has point-in-time restore; enable a scheduled snapshot for your data.

## Non-negotiable honesty note

"Free" PostgreSQL trial instances expire; Render free instances sleep and can change policy. This stack is a great **free start**, not a permanent production guarantee. Budget for paid tiers from day one of real use.