# Freelance Growth OS

A gamified learning roadmap for people starting to freelance: one road, six levels, 21 steps. The levels go Résumé basics → LinkedIn profile → Portfolio → Upwork & Fiverr → Client conversations → Deals & documents. Click a step to see what it covers.

Two pages are built: the roadmap and one lesson (Level 2, "Write your headline").

## What is in the repo

| Folder | What it is |
|---|---|
| `app/`, `components/`, `lib/` | The Next.js + TypeScript app |
| `data/roadmap.json` | All roadmap content (levels, steps, lesson parts). Both builds read it. |
| `prototype/` | The same two pages as plain HTML/CSS/JS. Open `prototype/index.html` in a browser; no build needed. |
| `design/` | Design source and screenshots (see below) |
| `scripts/sync-prototype.mjs` | Copies data, styles and fonts from the app into `prototype/` |

## Run the app

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
```

Routes: `/` is the roadmap and `/lessons/write-your-headline` is the lesson.

Progress is saved in `localStorage` (`lib/progress.ts`), so it survives a refresh. That file is the place to connect a real backend later. The map starts with 5 steps done as a demo; "Reset demo progress" at the bottom of the map puts it back.

## Editing

- **Content:** edit `data/roadmap.json`.
- **Styles:** edit `app/globals.css`. Each level has a colour theme (`.t-yellow`, `.t-blue`, …) set through four CSS variables.
- **3D tiles:** these are plain CSS, not WebGL. Each tile is one element with `rotateX(55deg) rotateZ(45deg)`, and stacked `box-shadow`s give it thickness.
- **Road shape:** `roadShape()` in `lib/roadmap.ts` sets where each step sits. It uses the `--pitch` and `--swing` values in the CSS.

After changing the data or the CSS, run `npm run sync:prototype` to update `prototype/`.

## Design

- Live design canvas: https://claude.ai/artifact/LV55gLhTzGJuvqECzcRbtQ (private to its owner until shared)
- `design/canvas/`: the canvas source files
- `design/screenshots/`: the roadmap on desktop and phone, and the lesson page

There is no Figma file yet. These screenshots and the canvas are the design reference.

## Not built yet

- Lesson pages for every step except "Write your headline". The other steps show "Lesson coming soon".
- Auth, a database, and AI rubric feedback. The headline checks are simple rules that run in the browser.
- The levels "Skill Development" and "Growth & Analytics" from the brief.
