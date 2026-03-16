# Expense Tracker - Deployment Guide

This guide covers deploying the Gmail Expense Tracker (React frontend + FastAPI backend + PostgreSQL).

---

## Architecture

```
┌──────────────────┐      ┌─────────────────────┐      ┌────────────────────┐
│  React SPA       │ ───▶ │  FastAPI Backend     │ ───▶ │  PostgreSQL (Neon)  │
│  (Vite build)    │      │  (Uvicorn)           │      │                     │
└──────────────────┘      └─────────────────────┘      └────────────────────┘
         │                            │
         │  VITE_API_URL              │  DATABASE_URL
         │  Cookie-based auth         │  GOOGLE_* (OAuth)
         └────────────────────────────┘
```

---

## Deployment Options

| Option | Frontend | Backend | DB | Best For |
|--------|----------|---------|-----|----------|
| **A. PaaS (Recommended)** | Vercel/Netlify | Railway/Render | Neon | Fastest, minimal DevOps |
| **B. Docker** | Nginx container | Python container | Neon or Postgres | Self-hosted, portable |
| **C. Single Server** | Nginx static | Systemd/Uvicorn | Local/Neon | VPS, full control |

---

## Option A: PaaS Deployment (Vercel + Railway + Neon)

### 1. Database (Neon)

1. Create a project at [neon.tech](https://neon.tech)
2. Copy the connection string (use **pooled** connection for serverless)
3. Format: `postgresql://user:pass@host/db?sslmode=require`

### 2. Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add **Authorized redirect URI**: `https://<your-backend-domain>/auth/callback`
   - Example: `https://expense-tracker-api.up.railway.app/auth/callback`
4. Copy Client ID and Client Secret

### 3. Backend (Railway / Render)

**Railway:**
1. Create project → Add service from GitHub repo
2. Root directory: `backend`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add env vars (see below)
5. Deploy → copy the public URL (e.g. `https://xxx.up.railway.app`)

**Render:**
1. New Web Service → connect repo
2. Root directory: `backend`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars

**Backend env vars (production):**

```
DATABASE_URL=postgresql://...
DATABASE_SSL=true
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://<backend-url>/auth/callback
JWT_SECRET=<32+ random chars>
ENCRYPTION_KEY=<fernet-key>
FRONTEND_URL=https://<frontend-url>
ENVIRONMENT=production
CORS_ORIGINS=https://<frontend-url>
ENABLE_DEBUG_API=false
```

**Generate secrets:**
```bash
# JWT_SECRET (32+ chars)
openssl rand -base64 32

# ENCRYPTION_KEY (Fernet)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Run migrations** (before first deploy or via release command):
```bash
cd backend && alembic upgrade head
```

### 4. Frontend (Vercel / Netlify)

**Vercel:**
1. Import project from GitHub
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. **Env var**: `VITE_API_URL=https://<backend-url>` (no trailing slash)

**Netlify:**
1. Add site from Git
2. Base directory: `frontend`
3. Build: `npm run build`
4. Publish: `dist`
5. Env: `VITE_API_URL=https://<backend-url>`

---

## Option B: Docker Deployment

### Prerequisites

- Docker & Docker Compose
- Neon DB (or local Postgres)

### Build & Run

```bash
# With Neon (DATABASE_URL in backend/.env)
cd Expense_Tracker
cp backend/.env.example backend/.env   # Edit with real values
docker compose up -d

# With local Postgres
docker compose --profile db up -d
# Set DATABASE_URL=postgresql://expense_tracker:expense_tracker_secret@db:5432/expense_tracker
# Set DATABASE_SSL=false in backend/.env

# Frontend: http://localhost
# Backend:  http://localhost:8000
```

### Run migrations (first deploy)

```bash
docker compose run --rm backend alembic upgrade head
```

### Docker local dev (Neon DB)

For local Docker with Neon, set in `backend/.env`:
- `CORS_ORIGINS=http://localhost`
- `FRONTEND_URL=http://localhost`

### Production Docker Compose

Set in `backend/.env`:
- `DATABASE_URL` (Neon connection string)
- `GOOGLE_*`, `JWT_SECRET`, `ENCRYPTION_KEY`
- `FRONTEND_URL` = your frontend domain
- `CORS_ORIGINS` = your frontend domain
- `ENVIRONMENT=production`

Build frontend with correct API URL:
```bash
cd frontend
VITE_API_URL=https://api.yourdomain.com npm run build
```

---

## Option C: Single Server (VPS)

### Nginx config example

```nginx
server {
    listen 80;
    server_name app.yourdomain.com;

    # Frontend (SPA)
    root /var/www/expense-tracker/frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Auth routes (no /api prefix in your app - adjust or add)
    location /auth/ {
        proxy_pass http://127.0.0.1:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /transactions/ { proxy_pass http://127.0.0.1:8000/transactions/; }
    location /analytics/ { proxy_pass http://127.0.0.1:8000/analytics/; }
    location /sync/ { proxy_pass http://127.0.0.1:8000/sync/; }
}
```

**Note:** If using a single domain, set `VITE_API_URL=` (empty or same origin) and configure Nginx to proxy all API paths. CORS and cookies will work on same domain.

### Systemd backend service

```ini
[Unit]
Description=Expense Tracker API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/expense-tracker/backend
EnvironmentFile=/var/www/expense-tracker/backend/.env
ExecStart=/var/www/expense-tracker/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Production Checklist

### Before Deploy

- [ ] `GOOGLE_REDIRECT_URI` in .env matches Google Console **exactly**
- [ ] `FRONTEND_URL` = production frontend URL
- [ ] `CORS_ORIGINS` includes production frontend URL
- [ ] `ENVIRONMENT=production`
- [ ] `ENABLE_DEBUG_API` not set or `false`
- [ ] `JWT_SECRET` and `ENCRYPTION_KEY` are strong and unique
- [ ] Database migrations: `alembic upgrade head`

### After Deploy

- [ ] Health: `GET {backend}/` returns 200
- [ ] Login flow works (redirect to Google → callback → dashboard)
- [ ] `/auth/me` returns user when logged in
- [ ] HTTPS everywhere (cookies need Secure in production)

---

## Environment Variables Reference

### Backend (required)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Must match Google Console |
| `JWT_SECRET` | Min 32 characters |
| `ENCRYPTION_KEY` | Fernet key for refresh tokens |
| `FRONTEND_URL` | Where to redirect after OAuth |

### Backend (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_SSL` | `true` | Set `false` for local Postgres |
| `ENVIRONMENT` | `development` | `production` for secure cookies |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated origins |
| `JWT_EXPIRATION_DAYS` | `7` | Session lifetime |
| `ENABLE_DEBUG_API` | `false` | Enable `/debug/db` |
| `LOG_LEVEL` | `INFO` | Logging level |

### Frontend (build-time)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API base URL (baked into build) |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 404 on /auth/google | Backend running? Correct port? |
| CORS errors | Add frontend URL to `CORS_ORIGINS` |
| Cookie not set | Same domain or correct `SameSite`; HTTPS in prod |
| OAuth "redirect_uri_mismatch" | `GOOGLE_REDIRECT_URI` must match Google Console exactly |
| DB connection failed | Check `DATABASE_URL`; use `DATABASE_SSL=false` for local |
| APScheduler duplicates | Use **1 worker** only (`--workers 1`) |
