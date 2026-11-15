# PeopleForce

A gamified learning path that helps skilled professionals start and grow a freelance business.
Learn something, apply it, keep a real asset, move on.

After the first run there is a daily loop: a two-minute daily challenge, a streak, XP ranks, and a
profile page (click your avatar) with your rank ladder, achievements and everything you have built.
The path is open-ended: 20 steps are mapped, 3 are playable, the rest are marked "Coming soon".

First-time journey, fully working: landing → 7-question quiz → personalized preview → email magic link
→ journey map → first lesson → avatar → XP → next lesson unlocked → guided tour complete.
Everything is persisted server-side, so refreshes, logouts and other devices resume where you stopped.

## What is in the repo

| Path | What it is |
|---|---|
| `app/`, `components/`, `lib/` | Next.js 16 web app (TypeScript, React Query, Zod, Driver.js, PostHog) |
| `api/` | FastAPI backend (Dishka, SQLAlchemy 2 async, Alembic, Pydantic v2, Adaptix), managed with `uv` |
| `studio/` | Sanity Studio schema for learning content |
| `e2e/` | Playwright test of the first-run journey |
| `docs/` | Architecture, flows, data model, content schema, action engine, AI, deployment, decisions, plan |
| `docker-compose.yml` | Production stack (web, api, migrate, postgres) for Dokploy |
| `prototype/`, `design/`, `data/roadmap.json` | The original static prototype and design sources (reference) |

## Run it locally

Needs Node 20+, `uv`, Docker.

```bash
# 1. Database
docker compose -f docker-compose.dev.yml up -d

# 2. API (http://localhost:8000, docs at /api/v1/docs)
cd api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn peopleforce.main:app_factory --factory --port 8000 --reload --reload-dir src

# 3. Web (http://localhost:3000), in a second terminal at the repo root
npm install
npm run dev
```

`PUBLIC_BASE_URL` in `api/.env` must be the address you open the web app on. If port 3000 is taken,
run `npx next dev -p 3100` and set `PUBLIC_BASE_URL=http://localhost:3100`.

With the default `EMAIL_PROVIDER=console`, no email is sent: the "check your inbox" screen shows the
sign-in link (development only), and the API log prints it.

AI feedback is off by default. To turn it on, set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` in `api/.env`.

## Checks

```bash
cd api && uv run pytest && uv run ruff check src tests alembic && uv run alembic check
npm run lint && npm run typecheck && npm run build
npm run test:e2e        # needs the three processes above; see playwright.config.ts
```

## Editing

- **Lesson content**: `api/content/software-development.json` (seed) or Sanity Studio (`docs/content-schema.md`).
- **Styles**: `app/globals.css` is the design system. Each level has a colour theme (`.t-yellow`, `.t-blue`, …).
  After changing it, `npm run sync:prototype` updates `prototype/`.
- **Quiz questions**: `api/src/peopleforce/modules/onboarding/quiz.py`.
- **Tour steps**: `components/tour/steps.ts` (presentation) and `api/src/peopleforce/modules/tours/service.py` (state machine).

## Documents

Start with `docs/architecture.md` and `docs/user-flow.md`. `docs/implementation-plan.md` lists what is
built, what was verified, and what is left. `docs/deployment.md` covers Dokploy.

## Not built yet

Buttons for the AI platform draft (the API exists), lesson content beyond the first chapter, a public profile page, and anything that needs accounts this repo does not have yet
(Resend, Sanity, PostHog and Langfuse are wired but unverified). Details in `docs/implementation-plan.md`.
