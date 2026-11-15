# Decisions

Each entry: what was decided, what else was considered, and the cost.

## D1. Keep the Next.js app at the repository root; add `api/` and `studio/` beside it
- **Alternatives**: move the app to `apps/web` in a monorepo.
- **Why**: the app, its config and the Next.js agent rules already lived at the root. Moving them would
  have been a large diff with no functional gain during a 24-hour build.
- **Cost**: the root `package.json` belongs to the web app; the root `tsconfig.json` and ESLint config
  exclude `api/` and `studio/` explicitly.

## D2. `globals.css` stays the design system; Tailwind is added without preflight
- **Context**: the stack calls for Tailwind, but the existing UI was plain CSS with its own tokens.
- **Decision**: Tailwind v4 utilities and theme only (`app/tailwind.css`), tokens mapped to the existing
  variables. Component looks stay in `globals.css`; new screens add classes in the same vocabulary.
- **Alternatives**: rewrite the UI in Tailwind (rejected: changes the look, the prototype sync script
  copies `globals.css`); skip Tailwind (rejected: stack requirement).
- **Cost**: two styling mechanisms. Rule: utilities for layout and spacing, classes for components.
  Utilities sit in a cascade layer, so an unlayered `globals.css` rule wins on the same property.
  In practice the new screens use the component classes almost exclusively.

## D3. Same-origin API through a Next.js rewrite
- **Alternatives**: Traefik path routing `/api` → api; a separate API subdomain with CORS.
- **Why**: first-party cookies, no CORS, one public service, identical behaviour in dev and prod.
- **Cost**: `API_INTERNAL_URL` is fixed at build time; API traffic passes through the Node process.
  Switching to Traefik path routing later needs no application change.

## D4. Signed-in screens are client-rendered with React Query
- **Why**: they are interactive and per-user; with Cache Components, reading the session on the server
  would force every page behind request-time rendering. The landing page stays a static Server Component.
- **Cost**: a loading state on first paint of `/journey`; `export const instant = false` on those pages.

## D5. Magic link: GET shows, POST consumes
- **Why**: mail security scanners fetch links. A GET that consumed the token would log real users out
  of their own link.
- **Detail**: token in the query string, removed with `history.replaceState` as soon as it is read;
  `Referrer-Policy: no-referrer` on the page; the PostHog client drops events from that URL.
- **Alternative**: token in the URL fragment (never reaches any server). Rejected because link
  rewriting by mail clients and click trackers is less predictable with fragments.

## D6. No redirect parameter after sign-in
- The destination is always `/journey`. An allow-list would also be safe, but nothing needs it yet,
  and no parameter means no open-redirect surface.

## D7. Rate limiting in PostgreSQL, no Redis
- Counts over `magic_link_challenges` (indexed) are enough at this scale. AI usage is limited the same
  way over `ai_generations`.
- **Cost**: not suitable for high-volume abuse protection; put a proxy-level limit in front if needed.

## D8. The avatar step belongs to progression, not to the tour
- The first lesson's reward is parked as `lesson_progress.status = reward_pending` until an avatar exists.
- **Why**: "skipping the tour must not block progress" and "no XP before the avatar" can only both hold
  if the tour is narration over a flow the progression engine owns.
- **Cost**: the avatar dialog cannot be dismissed. Choosing takes one click, and the work is saved either way.

## D9. Tour stages: six instead of seven
- `first_lesson_submitted` and `avatar_selection` from the brief are one stage (`avatar_selection`):
  the moment the lesson is submitted, the only thing to show is the avatar picker.
  `first_lesson_submitted` exists as the *event* that enters that stage.

## D10. Content: Sanity primary, bundled seed as development source and cold-start fallback
- **Why**: development and tests must not need a CMS account; a CMS outage on a cold start should
  degrade to known-good content rather than an error.
- **Cost**: the seed can drift from the CMS. `studio/scripts/seed-to-ndjson.mjs` exports the seed into a
  dataset so both start equal.
- **Not verified**: no Sanity project was available, so the GROQ query has not been run against a real
  dataset. The Studio schema type-checks, and the normalization of a Sanity-shaped result is unit-tested.

## D11. Blocks and actions are embedded in the lesson document
- As the brief suggests. Actions are defined once per lesson and placed in blocks by key, so one block
  can hold several actions and the engine can reason about actions without walking blocks.

## D12. Lesson snapshots by content hash instead of a release compiler
- Cheap to build, and it answers the real question ("what did the learner see when they submitted?").
- **Deferred**: named releases with activation timestamps.

## D13. Quiz questions and tour copy live in code
- The quiz drives typed personalization (enums used by examples, prompts and copy), so changing an
  option is a code change anyway. Tour copy is five strings.
- **Deferred**: CMS-managed tour variants and settings.

## D14. LLM: provider protocol with Gemini (used) and Anthropic adapters
- The team supplied Gemini credentials, so Gemini is the configured provider
  (`gemini-3.5-flash-lite`, an inexpensive model; one feedback call measured at about 2 seconds).
- The Anthropic adapter exists to prove the abstraction; it is untested against the live API.
- No agent framework: each capability is one structured call.

## D15. `submissions`, `onboarding_answers`, `achievements` are not separate tables
- See "Simplifications" in `data-model.md`.

## D16. No repository layer
- Services use the SQLAlchemy session directly. With one database and small modules, repositories
  would add indirection without a second implementation to justify them.

## D17. Typed API client is hand-written
- `lib/api/types.ts` mirrors the Pydantic schemas. Generating it from OpenAPI was not practical in the
  time available because lesson blocks and action configs are polymorphic and are exposed as open
  objects in the schema. **Risk**: drift. The Playwright test covers the main shapes.

## D18. PostHog: explicit events only
- Autocapture is off, inputs are masked, `[data-private]` text is masked in replays. Milestones that
  must not be double-counted (auth, lesson completion, XP, avatar, tour completion, asset creation) are
  sent by the server with the user id; the client sends funnel steps that happen before an account exists
  and identifies the visitor after sign-in so both halves join.

## D19. XP tiers are called "ranks"
- The map already labels chapters "Level 1…6". A second thing called "level" would be ambiguous, so the
  XP ladder is Newcomer → Independent ("Rank 2 of 7"). Thresholds live in code (`gamification/ranks.py`).

## D20. Streaks are computed from activity days, not stored as a counter
- `activity_days` holds one row per local day. Current and longest streak are derived on read.
- **Why**: a stored counter needs a nightly reset job and breaks when the time zone changes; a set of
  days is always right. A streak stays alive through the end of the next day.
- **Cost**: reads every activity day of the user; fine for years of data, cache later if needed.

## D21. Daily challenge selection is a rotation, not random and not AI
- `(day number + user id) mod pool size`: stable across refreshes, different between learners, no state
  until the learner answers. Challenges are content and reuse the lesson action types.

## D22. Lessons are played one step per screen
- The scrolling lesson page showed reading, a four-field form, feedback and saving at once. Now each
  block and each action is a step, a text exercise asks one question at a time, and the side column is
  gone. The profile facts it showed live on the profile page.
- **Cost**: more clicks per lesson; in exchange each screen has one thing to do.

## D23. The path is open-ended
- No finish line. Unwritten lessons are published as topics ("Coming soon"); the map ends with what is
  planned next. Sequential unlocking stops at the first topic without content.

## D24. Daily challenges are real-world tasks with a self-reported count
- "Write to 5 potential clients", not a quiz. Implemented as the `external_task` action type
  (`target_count`, `unit`, `tips`); progress is a tick per unit, saved server-side.
- **Trade-off**: the app cannot verify outreach, so the count is the learner's word. The UI states that
  plainly. XP per challenge is modest (15–30) so honesty costs little.

## D25. Product name is PeopleForce
- Renamed from the working name everywhere: UI, emails, Python package (`peopleforce`), cookies
  (`pf_session`, `pf_onb`), database name and user, Docker and docs. The dev database moved to a new
  volume (`peopleforce_dev_pg`); the old dev volume was left in place, unused.

## Deferred features

| Feature | State |
|---|---|
| AI platform draft in the UI | API built and tested; saved assets are listed on the profile page, the generate / approve buttons are not built |
| Streak freeze, reminders, leaderboards | Not started |
| Lessons beyond chapter 1 | Map entries only ("coming soon") |
| YouTube video in a lesson | Block type built; no video in the seed |
| Public freelancer profile, client inquiry form | Not started |
| `publish_asset`, conversation, document actions | Reserved names, rejected by validation |
| Content webhooks / instant cache invalidation | Not started (60 s polling cache) |
| Cleanup job for expired drafts, challenges, sessions | Not started; expired rows are ignored by queries |
| Display name collection | Column exists, never asked |
| Payments, OAuth, social posting, scraping | Out of scope |
