# Implementation plan

State of the repository on 2026-11-15, what was built in the first pass, and what remains.

## Repository findings (audit)

| Area | Found |
|---|---|
| Framework | Next.js 16.4.6 (App Router, Turbopack, `cacheComponents`, `partialPrefetching`), React 19.3, TypeScript strict |
| Styling | One hand-written stylesheet (`app/globals.css`, 1,329 lines), CSS variables, one colour theme per level. No Tailwind, no component library |
| Screens | `/` roadmap (6 levels, 21 steps) and `/lessons/write-your-headline` (one hard-coded lesson) |
| Data | `data/roadmap.json` (web-designer copy); progress in `localStorage`, seeded with five demo steps |
| Backend, auth, database, CMS, AI, analytics, deployment | None |
| Other | `prototype/` (static HTML copy of the two screens), `design/` (canvas source, screenshots), `scripts/sync-prototype.mjs` |
| Git | Clean, one commit |

**Kept as the visual source of truth**: `globals.css`, the map components (`RoadmapMap`, `StepNode`,
`StepDrawer`, `Hero`, `TopBar`), the lesson layout classes, icons, fonts.

**Architectural problems found**: progress and XP decided in the browser; lesson content hard-coded in
a component; "Mark as done" let the client complete any step; the brand and copy were for another
product name and audience.

## What changed in existing code

| File | Change |
|---|---|
| `components/roadmap/*` | Same markup and classes. Data now comes from props (API) instead of a module-level JSON import; statuses come from the server. "Mark as done" and "Reset demo progress" removed. A `data-tour` anchor added to the current checkpoint |
| `components/roadmap/Roadmap.tsx` | Replaced by `components/journey/JourneyScreen.tsx` (same composition) |
| `components/lesson/HeadlineLesson.tsx`, `app/lessons/…` | Removed. Its layout lives on in the generic `components/lessons/LessonScreen.tsx` |
| `lib/progress.ts` | Removed (`localStorage` progress). `useIsWide` moved to `lib/useIsWide.ts` |
| `lib/roadmap.ts` | Types and `roadShape` kept; data helpers now work on API types |
| `app/page.tsx` | Now the landing page. The map moved to `/journey` |
| `app/globals.css` | Existing rules untouched; a new section appended for the new screens |
| `data/roadmap.json`, `prototype/`, `design/` | Untouched (still the design reference) |

## Built and verified

| Requirement | Status | Evidence |
|---|---|---|
| Visual theme preserved | done | Same stylesheet and components; screenshots from the e2e run |
| Landing with CTAs | done | five CTAs → `/start`, each tracked with its location |
| Seven-question quiz, one per screen, back, progress, resume | done | e2e reloads mid-quiz |
| Anonymous quiz persistence | done | server-side draft, opaque cookie; API tests |
| Personalized preview before email | done | e2e asserts no email field before "Save my journey" |
| Magic-link auth (single use, expiry, hashed, rate limited, scanner-safe, logout) | done | `tests/test_auth_and_onboarding.py` (9 tests) |
| Account and quiz linking, cross-device | done | `test_link_opened_on_another_device_still_links_the_quiz` |
| Journey map with current checkpoint | done | e2e |
| First-time tour across screens, persisted | done | e2e reloads at steps 1, 3 and 4; skip and replay tested at API level |
| First lesson from content, functional action, persisted submission | done | e2e; content comes from the seed through the same validation path as Sanity |
| Avatar after the lesson, then XP | done | API asserts zero XP rows before the avatar |
| Idempotent XP | done | concurrent and repeated calls → one ledger row |
| Next checkpoint unlocks; locked lessons refuse direct navigation | done | API 403 + e2e |
| Returning user after logout | done | e2e: no tour, no dialogs, XP intact |
| Second and third lessons (quiz, acknowledge, bio) | done at API level | lesson 2 tested end to end in `test_later_lessons_pay_immediately…`; lesson 3 uses the same action types as lesson 1 |
| AI feedback | done | live call with Gemini returned valid structured feedback; failure path tested |
| Saved assets, achievements | done | four achievements defined, two earned in the first lesson |
| PostHog instrumentation | server side verified | 15 server events arrived in the EU project; funnel and dashboard created. Browser events are sent only by real browsers (PostHog drops automated ones), so they are unverified until a person clicks through |
| Docker Compose deployment | done locally | images built, stack started, migrate ran once, quiz → link → journey worked through the containers, data survived a restart |
| Dokploy deployment | not done | no server access; `deployment.md` has the steps |
| CMS editing | written, not verified | Studio schema type-checks; no Sanity project to run it against |
| Langfuse | done | live traces fetched and audited; prompts uploaded and linked; cost missing until a model price is added |
| Resend | written, not verified | no key; console sender used |

| Open-ended path: 20 topics, 3 playable, rest "Coming soon", no finish line | done | e2e asserts "More coming soon" and "Coming soon" |
| Step-by-step lesson player, one question per screen, shorter copy | done | e2e walks the five steps and resumes after a reload |
| Daily challenge + streak (time-zone aware, XP once per day) | done | API test with concurrent submits; e2e completes one |
| XP ranks and rank-up | done | unit + API tests; e2e sees "Rank up! You are now Explorer." |
| Profile page (avatar opens it; ladder, streak, achievements, assets, change character) | done | e2e |

Test totals: 30 API tests (pytest, real PostgreSQL), 1 Playwright journey, web lint + typecheck + build clean.

## Remaining work, in priority order

| # | Task | Depends on | Size |
|---|---|---|---|
| 1 | Create Resend, Sanity, PostHog, Langfuse accounts; put keys in Dokploy | – | 1 h |
| 2 | Deploy to Dokploy; send a real magic link to a real inbox (check link rewriting, spam folder) | 1 | 1–2 h |
| 3 | Import the seed into Sanity, run with `CONTENT_SOURCE=sanity`, fix any GROQ mismatch | 1 | 1–2 h |
| 4 | Platform draft on the profile page: generate / edit / approve (API exists; saved assets are already listed there) | – | 2 h |
| 5 | Verify PostHog events and build the funnel below | 1, 2 | 1 h |
| 6 | Add a vetted YouTube video to lesson 1 in Studio | 3 | 15 min |
| 7 | Lesson content for chapter 2 (LinkedIn) | 3 | editorial |
| 8 | Phone pass on quiz, lesson and dialogs (CSS is responsive but only desktop was exercised) | – | 1–2 h |
| 9 | Cleanup job for expired drafts, challenges and sessions | – | 1 h |
| 10 | Portfolio case-study lesson and asset type | 3 | 3 h |

Parallel tracks: (1→2→5) infrastructure, (3→6→7) content, (4, 8) frontend, (9, 10) backend.

## 24-hour schedule

| Hours | Work | State |
|---|---|---|
| 0–1 | Audit, decisions, module boundaries | done |
| 1–6 | API: models, migration, auth, onboarding, content, actions, progression, tour, AI; tests | done |
| 6–10 | Web: API client, landing, quiz, preview, auth, journey, lesson player, avatar, reward, tour | done |
| 10–12 | Dockerfiles, Compose, local production run, Playwright journey, documents | done |
| 12–14 | Accounts and keys, Dokploy deploy, real email test (tasks 1–2) | open |
| 14–16 | Sanity import and live content (task 3, 6) | open |
| 16–19 | Assets screen with the AI platform draft (task 4) | open |
| 19–21 | Phone pass, PostHog funnel (tasks 5, 8) | open |
| 21–23 | Rehearse the demo on production, fix what it finds | open |
| 23–24 | Buffer | – |

## Activation funnel (PostHog)

| Step | Event | Sent by |
|---|---|---|
| Landing CTA | `landing_cta_clicked` (`location`) | client |
| Quiz started | `onboarding_started` | client |
| Quiz completed | `onboarding_completed` | client |
| Preview seen | `journey_preview_viewed` | client |
| Email requested | `email_link_requested` (`source`) | client |
| Auth completed | `authentication_completed` (`is_new_user`, `draft_linked`) | server |
| First lesson started | `first_lesson_started` | server |
| First lesson completed | `first_lesson_completed` | server |
| Avatar chosen | `avatar_selected` | server |
| XP earned | `xp_awarded` (`amount`) | server |
| Second lesson started | `lesson_started` (`lesson_id = spot-a-strong-offer`) | server |

Also sent: `onboarding_question_answered`, `journey_viewed`, `lesson_viewed`, `tour_step_viewed`,
`tour_started`, `tour_skipped`, `tour_completed`, `action_submitted`, `lesson_completed`,
`next_lesson_unlocked`, `achievement_earned`, `freelancer_asset_created`, `freelancer_asset_approved`.
Not sent (features not built): `profile_published`, `platform_content_exported`.

Client events before sign-in use PostHog's anonymous id; after sign-in the client calls
`identify(user.id)`, which merges that history with the server events sent under the user id.
Properties are ids, enums and counts only.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Magic-link email lands in spam or the link is rewritten by click tracking | medium | blocks sign-in | verified sending domain, click tracking off, test with real inboxes early |
| GROQ projection does not match the Studio schema in some field | medium | lessons show as "coming soon" | per-lesson validation logs the exact error; seed fallback keeps the demo alive |
| `PUBLIC_BASE_URL` wrong in production | medium | every write returns 403 | documented; health check does not catch it, so test sign-in right after deploy |
| LLM quota or latency during the demo | low | feedback button fails | feedback is optional; failure is recoverable; 45 s timeout |
| Hand-written API types drift from the backend | medium | runtime UI errors | Playwright journey; generate types later |
| Next.js 16 Cache Components surprises on new routes | low | build fails | signed-in routes are client-rendered behind Suspense; build is part of the checks |
| Phone layout issues in new screens | medium | poor demo on mobile | task 8 |
| Editors change a lesson slug | low | learners' progress on that lesson is orphaned | documented in Studio field descriptions |

## Definition of done

A change is done when:

1. `uv run pytest`, `uv run ruff check`, `uv run alembic check` pass in `api/`.
2. `npm run lint`, `npm run typecheck`, `npm run build` pass.
3. `npm run test:e2e` passes against the local stack.
4. Any new state transition is persisted and survives a refresh.
5. Any new reward path goes through the XP ledger with an idempotency key.
6. New inputs (request, CMS, model) are validated before use.
7. No domain rule was added to a React component.
8. The relevant document in `docs/` says what is true now, including what was not verified.

The product is demo-ready when the Playwright journey passes against the Dokploy deployment with a
real email inbox.
