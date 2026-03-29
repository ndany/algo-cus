# Deployment Guide — Progressive Scaling Roadmap

This document covers how to deploy AlgoStation today and how to evolve the deployment as usage grows.

## Current Architecture

```
User → Render (free tier, single process)
         └─ Dash app (gunicorn, 2 workers)
              ├─ yfinance (on-demand per request, 2-5s)
              └─ Supabase (auth + invitation codes)
```

**Key characteristics:**
- Single Python process behind gunicorn
- On-demand data fetching (no background workers)
- Supabase handles all persistent state (auth, invitation codes)
- No caching layer beyond yfinance's built-in session cache
- Ephemeral filesystem (files written to disk are lost on restart)

---

## Stage 1: Initial Deployment (Current)

**When**: Now
**Cost**: Free
**Supports**: 1-5 concurrent users

### Render Setup

1. Create a Render account at https://render.com
2. Connect your GitHub repository
3. Create a new **Web Service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn dashboard.app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --preload`
   - **Instance Type**: Free
4. Set environment variables:
   - `SUPABASE_URL` — from your Supabase project
   - `SUPABASE_KEY` — Supabase anon/public key
   - `SKIP_AUTH` = `0`
   - `DASH_DEBUG` = `0`
   - `PYTHON_VERSION` = `3.11.8`

### Supabase Setup

1. Create a free Supabase project at https://supabase.com
2. Enable Google OAuth:
   - Supabase Dashboard → Authentication → Providers → Google → Enable toggle
   - Create Google OAuth credentials (see steps below)
   - Paste the **Client ID** and **Client Secret** into the Supabase Google provider form
   - Set the redirect URL to your Render app URL + `/auth/callback`

   **Creating Google OAuth Credentials:**

   a. Go to https://console.cloud.google.com and create a new project (or select an existing one)
      - Project name: e.g. `AlgoStation` (any name works, users won't see this)
   b. Navigate to **APIs & Services → OAuth consent screen**
      - User type: **External** (unless you have Google Workspace and want to restrict to your org)
      - App name: `AlgoStation` (shown to users on the Google sign-in page)
      - User support email: your email
      - App logo: optional, skip for now
      - App domain / Authorized domains: add your Render domain (e.g. `your-app.onrender.com`)
      - Developer contact email: your email
      - Scopes: click **Add or Remove Scopes** → select `email` and `profile` (`.../auth/userinfo.email` and `.../auth/userinfo.profile`) → Save
      - Test users: add your own email (required while in "Testing" status — only listed test users can sign in until you publish the app)
      - Click **Save and Continue** through to the summary, then **Back to Dashboard**
   c. Navigate to **APIs & Services → Credentials**
      - Click **+ Create Credentials → OAuth client ID**
      - Application type: **Web application**
      - Name: `AlgoStation Web` (internal label, anything works)
      - Authorized JavaScript origins: add `https://your-app.onrender.com` (and `http://localhost:8050` for local dev)
      - Authorized redirect URIs: `https://<your-supabase-ref>.supabase.co/auth/v1/callback` (Supabase handles the Google callback, then redirects to your app)
      - Click **Create**
   d. Copy the **Client ID** and **Client Secret** from the dialog that appears — paste these into Supabase

   > **Publishing note:** While the app is in "Testing" status, only emails you added as test users can sign in. To allow anyone with a Google account, go back to OAuth consent screen → **Publish App**. Google may show an "unverified app" warning to users — this is normal for small projects and doesn't require verification unless you exceed 100 users.
3. Run database migrations:
   - Open Supabase Dashboard > SQL Editor
   - Run each file in `sql/migrations/` in order (001, 002, 003, ...)
   - See `sql/README.md` for details

4. Insert some invitation codes:
   ```sql
   INSERT INTO invitation_codes (code) VALUES
       ('ALGO-DEMO-2026'),
       ('TRADE-BETA-001'),
       ('QUANT-LEARN-42');
   ```

### Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| **Cold start** (~30s after 15min idle) | First visitor waits 30s | Use UptimeRobot free tier to ping every 14min (eliminates cold starts entirely) |
| **512MB RAM** | Limits concurrent analyses | 2 workers handle ~5 concurrent users |
| **No persistent disk** | Can't cache data to disk | yfinance in-memory session cache; repeat visitors re-fetch |
| **2-5s per analysis** | Noticeable wait on each ticker | Show loading spinner; acceptable for learning tool |

### Eliminating Cold Starts (Free)

Sign up at https://uptimerobot.com (free tier: 50 monitors) and add an HTTP monitor pointing to your Render URL. Set the check interval to 14 minutes. This keeps the process alive permanently.

### Staging Environment

A staging service lets you test code changes on Render before deploying to production.

**Render setup:**
1. Create a second **Web Service** in Render (requires credit card on file — no charges on free tier)
2. Connect the same GitHub repository
3. Set **Branch** to your feature branch (e.g., `feature/usage-telemetry`)
4. Same build command, start command, and environment variables as production
5. Staging URL will be `https://algo-cus-staging.onrender.com` (or whatever name you choose)

**Google OAuth — add staging redirect URI:**
- Google Cloud Console → APIs & Services → Credentials → your OAuth client
- Under **Authorized redirect URIs**, add: `https://algo-cus-staging.onrender.com/auth/callback`
- Note: Google's `redirect_uri` goes to Supabase (`<ref>.supabase.co/auth/v1/callback`), not your app directly. The Supabase callback URL should already be listed from initial setup.

**Supabase — add staging redirect URL:**
- Supabase Dashboard → Authentication → URL Configuration → Redirect URLs
- Add: `https://algo-cus-staging.onrender.com/auth/callback`

**What's shared between production and staging:**
- Same Supabase project (auth, telemetry, invitation codes)
- Same Google OAuth client (multiple redirect URIs supported)
- Telemetry data mixes between environments — filter by Render logs if needed

---

## Stage 2: Always-On + In-Memory Caching

**When**: You want consistent response times, or have 5-15 regular users
**Cost**: ~$7/month (Render Starter)
**Benefit**: No cold starts, faster repeat analyses, better multi-user experience

### Changes

1. **Upgrade Render to Starter plan ($7/month)**
   - Always-on (no sleeping)
   - 512MB → 512MB RAM (same, but no cold start penalty)

2. **Add in-memory data caching in the app**
   ```python
   # dashboard/analysis.py — add TTL cache
   from functools import lru_cache
   import time

   _cache = {}
   CACHE_TTL = 4 * 3600  # 4 hours

   def get_cached_data(ticker):
       if ticker in _cache:
           data, timestamp = _cache[ticker]
           if time.time() - timestamp < CACHE_TTL:
               return data
       data = MarketDataProvider().fetch(ticker, period="2y")
       _cache[ticker] = (data, time.time())
       return data
   ```

3. **Add 3-4 workers** to handle concurrent requests:
   ```
   gunicorn dashboard.app:server --workers 4 --timeout 120
   ```

### What This Gets You

| Before (Free) | After ($7/month) |
|---------------|-----------------|
| 30s cold start | Instant (always on) |
| Every analysis re-fetches | Repeat tickers served from cache in <1s |
| ~2 concurrent users | ~10 concurrent users |

---

## Stage 3: Persistent Cache + Background Refresh

**When**: 10-30 regular users, or you want sub-second responses for common tickers
**Cost**: ~$14/month (Render Starter + Supabase remains free)
**Benefit**: Near-instant responses, resilience to yfinance outages

### Changes

1. **Use Supabase PostgreSQL for data caching**
   - Store fetched OHLCV data in a `market_data_cache` table
   - Query from Supabase instead of yfinance when cache is fresh
   - This uses the free Supabase DB you already have (500MB storage)

   ```sql
   CREATE TABLE market_data_cache (
       ticker TEXT NOT NULL,
       fetch_date DATE NOT NULL,
       data_json JSONB NOT NULL,
       fetched_at TIMESTAMPTZ DEFAULT NOW(),
       PRIMARY KEY (ticker, fetch_date)
   );
   ```

2. **Lazy background refresh**
   - Serve cached data immediately
   - If cache is >4 hours old, trigger a background thread to refresh
   - User never waits for yfinance

3. **Pre-warm popular tickers**
   - On app startup, fetch the default ticker list (AMZN, GOOG, JPM, MSFT) in a background thread
   - First visitors see instant results for these tickers

### What This Gets You

| Before ($7/month) | After ($14/month) |
|-------------------|------------------|
| 2-5s for first analysis per ticker | <1s for pre-warmed tickers |
| Data lost on restart | Data persists across restarts |
| yfinance outage = broken app | yfinance outage = slightly stale data |

---

## Stage 4: Dedicated Compute + Redis

**When**: 30-100 users, or you add computationally expensive features (ensemble optimization, parameter sweeps)
**Cost**: ~$25-35/month
**Benefit**: True concurrency, fast parameter sweeps, real-time feel

### Changes

1. **Upgrade Render to Standard plan ($25/month)**
   - 2GB RAM, 1 vCPU
   - 8+ workers for concurrent requests

2. **Add Redis for caching ($0 — Render free Redis, or Upstash free tier)**
   - Replace in-memory cache with Redis
   - Shared cache across all workers (critical with 8+ workers)
   - TTL-based expiration
   - Sub-millisecond cache reads

3. **Move heavy computation to background tasks**
   - Walk-forward analysis takes several seconds
   - Run in a background thread, push results to Redis
   - Frontend polls for completion (or use server-sent events)

### What This Gets You

| Before ($14/month) | After (~$30/month) |
|--------------------|-------------------|
| 4 workers, some contention | 8+ workers, handles bursts |
| Per-worker cache (duplicated) | Shared Redis cache (efficient) |
| Walk-forward blocks the request | Walk-forward runs in background |
| ~10 concurrent users | ~50 concurrent users |

---

## Stage 5: Separated Frontend + API

**When**: 100+ users, or you want a richer UI (React), mobile support, or public API
**Cost**: ~$30-50/month
**Benefit**: Independent scaling, better UX, API for integrations

### Changes

1. **Split into two services:**
   - **Frontend**: Next.js/React on Vercel (free tier)
   - **API**: FastAPI on Render ($25/month)

2. **API serves JSON, frontend renders charts client-side**
   - Use Plotly.js (same chart library, JavaScript version)
   - API returns data + metrics, frontend handles rendering
   - Enables mobile-responsive layouts more easily

3. **Add WebSocket support for live updates**
   - Server pushes analysis progress (10%... 50%... done)
   - No polling needed

### What This Gets You

| Before (~$30/month) | After (~$40/month) |
|--------------------|-------------------|
| Single monolith | Frontend scales independently |
| Dash renders server-side | Client-side rendering (faster feel) |
| Desktop-only UX | Responsive mobile support |
| No API | REST API for scripts/notebooks |

---

## Decision Matrix

Use this to decide when to move to the next stage:

| Signal | Action |
|--------|--------|
| You're the only user, exploring | Stay at Stage 1 (Free) |
| Cold starts annoy you | Add UptimeRobot (Free) or Stage 2 ($7/month) |
| Sharing with 5-10 people | Stage 2 ($7/month) |
| Same tickers analyzed repeatedly | Stage 3 ($14/month) |
| Adding ensemble/optimization features | Stage 4 (~$30/month) |
| Want mobile support or public API | Stage 5 (~$40/month) |
| 100+ users or commercial use | Stage 5 with paid Vercel Pro ($60+/month) |

## Cost Summary

| Stage | Monthly Cost | Concurrent Users | Response Time (cached) |
|-------|-------------|-----------------|----------------------|
| 1. Free + UptimeRobot | $0 | ~5 | 2-5s always |
| 2. Always-on + memory cache | $7 | ~10 | <1s repeat, 2-5s new |
| 3. Persistent cache | $14 | ~20 | <1s most tickers |
| 4. Redis + more compute | $30 | ~50 | <500ms cached |
| 5. Separated frontend/API | $40+ | 100+ | <200ms cached |

Each stage builds on the previous one — no "big bang" migration. The core Python logic (strategies, backtests, walk-forward) stays the same throughout.
