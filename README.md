# Briefly - a daily AI research podcast

Enter a research topic and a daily time. Every day at that time you get an email with a link to a
five-minute audio episode on that topic, researched from current news by an agent and voiced with
Gnani.ai text-to-speech.

> Example: *"Find all startup funding announced in the last 24 hours"*, every day at 8:00 AM.

---

## Features

- Email + password sign-in; every user sees only their own briefings and episodes.
- Create, edit, pause/resume and delete briefings (topic + daily time + timezone).
- Each day, in the background: research → ~5-minute script → Gnani TTS → MP3 → email.
- The email arrives at the chosen time, not when generation happens to finish.
- Episode page with audio player, summary, source links and full transcript.
- "Generate now" for an immediate episode.

## Architecture

```
┌──────────────┐  Supabase JWT   ┌──────────────────────────────────────┐
│  Next.js     │ ──────────────▶ │  FastAPI on Render (single instance) │
│  (Vercel)    │   REST / JSON   │   ├─ REST API                        │
│              │                 │   ├─ APScheduler: one daily cron job │
│ Supabase Auth│                 │   │   per briefing + one-off email   │
│ email+pass   │                 │   │   jobs at delivery time          │
└──────────────┘                 │   └─ thread pool runs the pipeline   │
   cron-job.org ── GET /health ──▶   (every 5 min, keeps Render awake) │
                                 └───────────────┬──────────────────────┘
          ┌──────────────┬──────────────┬────────┴─────┬──────────────┬────────────┐
          ▼              ▼              ▼              ▼              ▼            ▼
     Supabase        Groq LLMs       Tavily       Gnani.ai TTS    Supabase      Brevo
     Postgres     (OpenRouter free   (news         (script →      Storage      (email)
                     fallback)       search)        audio)       (private mp3)
```

**Episode pipeline:** plan search queries (LLM) → search news from the last day (Tavily) → write a
spoken script from those articles only (LLM) → synthesize audio (Gnani) → upload MP3 (Supabase
Storage) → email at the delivery time (Brevo).

## Tech stack

| Concern | Choice |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS — Vercel |
| Backend | FastAPI, Python - Render |
| Database / Auth / Storage | Supabase (Postgres, email+password auth, private bucket) |
| Scheduling | APScheduler inside the API process, Postgres as source of truth |
| LLM | Groq (`gpt-oss-120b` → `qwen3.8-27b` → `gpt-oss-20b`), then OpenRouter free models |
| Web search | Tavily (news, last-day filter) |
| Text-to-speech | Gnani.ai (Vachana TTS REST API) |
| Email | Brevo transactional HTTP API |
| Keep-alive | cron-job.org → `GET /health` every 5 min |

## Project structure

```
backend/
  app/
    main.py          FastAPI app; starts/stops scheduler, DB pool, thread pool
    config.py        settings from environment variables
    auth.py          Supabase JWT verification
    db.py            Postgres connection pool + helpers
    migrate.py       applies migrations/*.sql
    timeutil.py      next run time (timezone + lead time)
    scheduler.py     per-briefing cron jobs, claims, catch-up, email delivery jobs
    pipeline.py      one episode end to end; also a CLI for local debugging
    routes/          briefings.py, episodes.py
    services/        llm.py, search.py, research.py, tts.py, storage.py, email.py
  migrations/        001_init.sql, 002_scheduled_delivery.sql
frontend/
  proxy.ts           route protection
  app/               login, signup, (app)/ dashboard, briefings/[id], episodes/[id]
  components/        forms, cards, lists, episode/briefing views, status badge
  lib/               API client, Supabase client, formatting, polling hook
```

## Running locally

**Prerequisites:** Python 3.12+, Node.js 20+, and free accounts for Supabase, Groq, OpenRouter,
Tavily, Gnani.ai and Brevo.

**Supabase setup:** create a project, a **private** storage bucket named `episodes`, and enable
the Email auth provider.

**Backend**
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in the values (see below)
.venv/bin/python -m app.migrate
.venv/bin/uvicorn app.main:app --port 8000
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env          # fill in the values (see below)
npm run dev                   # http://localhost:3000
```

**Debugging the pipeline without the app** (writes to `backend/output/`, no database):
```bash
.venv/bin/python -m app.pipeline "startup funding announced in the last 24 hours"
.venv/bin/python -m app.pipeline --tts-only "Hello, this is a short voice test."
```

## Environment variables

**Backend** (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase Postgres **session pooler** connection string (IPv4) |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase secret key (storage access) |
| `SUPABASE_JWT_SECRET` | Only for projects still on the legacy HS256 secret; leave empty to use JWKS |
| `GROQ_API_KEY` / `GROQ_MODELS` | Groq key and comma-separated models, tried in order |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODELS` | OpenRouter key and free models used as fallback |
| `TAVILY_API_KEY` | Tavily search |
| `GNANI_API_KEY` | Gnani.ai TTS key |
| `GNANI_MODEL`, `GNANI_VOICE_ID`, `GNANI_LANGUAGE`, `GNANI_MAX_CHARS` | Optional; default `timbre-v2.5`, `Kaveri`, `en-IN`, `500` |
| `BREVO_API_KEY`, `EMAIL_FROM`, `EMAIL_FROM_NAME` | Brevo API key and a verified sender |
| `FRONTEND_URL` | Frontend origin — used for CORS and for links in emails |
| `GENERATION_LEAD_MINUTES` | How early generation starts (default `10`) |

**Frontend** (`frontend/.env`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Same as `SUPABASE_URL` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase publishable (anon) key |
| `NEXT_PUBLIC_API_URL` | Backend URL |

## API

All routes except `/health` need `Authorization: Bearer <Supabase access token>`.
Interactive docs at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check / keep-alive |
| GET, POST | `/briefings` | List / create (`topic`, `time_of_day`, `timezone`) |
| GET, PATCH, DELETE | `/briefings/{id}` | Read / edit or pause-resume / delete |
| POST | `/briefings/{id}/run` | Generate an episode now (409 if one is already generating) |
| GET | `/episodes?briefing_id=` | List episodes |
| GET | `/episodes/{id}` | Episode detail with a signed audio URL (held until delivery time) |