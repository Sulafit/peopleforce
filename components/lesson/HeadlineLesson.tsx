"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowIcon, CheckIcon, StarIcon } from "@/components/icons";
import { useProgress } from "@/lib/progress";

const STEP_ID = "l2s2";
const LIMIT = 220; // LinkedIn headline limit; recheck before launch.
const STARTING_DRAFT = "Web designer for B2B SaaS startups · landing pages that explain the product in one scroll";

const PARTS = [
  { title: "What a headline does", meta: "Read · 3 min" },
  { title: "Three patterns that work", meta: "Read · 3 min" },
  { title: "Draft yours", meta: "Practice · 6 min" },
  { title: "Save to your profile", meta: "Create · 3 min" },
];

/*
  Quick checks are deterministic on purpose: facts and state changes stay in code.
  Coaching feedback against the rubric belongs to the AI service on the backend.
*/
const CHECKS: { label: string; test: (text: string) => boolean }[] = [
  { label: `${LIMIT} characters or fewer`, test: (text) => text.length > 0 && text.length <= LIMIT },
  { label: "Says who it is for", test: (text) => /\bfor\b|\bhelp/i.test(text) },
  { label: "No filler titles such as guru, ninja or rockstar", test: (text) => text.length > 0 && !/guru|ninja|rockstar|wizard/i.test(text) },
];

/** Lesson for Level 2, step 2: write a LinkedIn headline. */
export function HeadlineLesson() {
  const { markDone } = useProgress();
  const [draft, setDraft] = useState(STARTING_DRAFT);
  const [saved, setSaved] = useState(false);

  const canSave = draft.length > 0 && draft.length <= LIMIT;

  const partState = (index: number) => {
    if (index < 2 || saved) return " is-done";
    return index === 2 ? " is-active" : "";
  };

  const save = () => {
    setSaved(true);
    markDone(STEP_ID); // saving the artifact completes the step on the roadmap
  };

  return (
    <div className="wrap t-blue">
      <header className="topbar">
        <Link className="btn btn--sm" href="/">
          <ArrowIcon back />
          Roadmap
        </Link>
        <div className="pills">
          <span className="pill pill--sm pill--level cap">Level 2 · LinkedIn profile</span>
          <span className="pill pill--sm">Step 2 of 4</span>
          <span className="pill pill--sm pill--xp">
            <StarIcon size={14} />
            +40 XP
          </span>
        </div>
      </header>

      <ol className="lesson-parts" aria-label="Lesson parts">
        {PARTS.map((part, index) => (
          <li key={part.title} className={`lesson-part${partState(index)}`}>
            <div className="lesson-part__bar" />
            <div>
              <span className="lesson-part__title">{part.title}</span>
              <span className="lesson-part__meta">{part.meta}</span>
            </div>
          </li>
        ))}
      </ol>

      <main className="lesson">
        <div className="lesson__main">
          <div className="lesson__intro">
            <span className="cap">Part 3 of 4 · Practice</span>
            <h1>Draft your headline</h1>
            <p>
              The headline is the one line shown next to your name in search, comments and messages. Build it from three
              pieces, in this order.
            </p>
          </div>

          <ol className="pattern">
            {["What you do", "Who it is for", "What they get"].map((piece, index) => (
              <li key={piece}>
                <span className="part__n">{index + 1}</span>
                {piece}
              </li>
            ))}
          </ol>

          <div className="card">
            <div className="field-group">
              <label htmlFor="headline">Your headline</label>
              <textarea
                id="headline"
                className="field"
                rows={3}
                value={draft}
                onChange={(event) => {
                  setDraft(event.target.value);
                  setSaved(false);
                }}
              />
              <div className="field-foot">
                <span>Started from your service pitch in Level 1.</span>
                <span className={`count${draft.length > LIMIT ? " is-over" : ""}`} aria-live="polite">
                  {draft.length} / {LIMIT}
                </span>
              </div>
            </div>

            <div>
              <h2 className="cap section-label">Quick checks</h2>
              <ul className="checks">
                {CHECKS.map((check) => {
                  const ok = check.test(draft);
                  return (
                    <li key={check.label} className={`check${ok ? " is-ok" : ""}`}>
                      <span className="check__mark" role="img" aria-label={ok ? "Passed" : "Not yet"}>
                        {ok && <CheckIcon />}
                      </span>
                      {check.label}
                    </li>
                  );
                })}
              </ul>
              <p className="hint" style={{ marginTop: 12 }}>
                After you save, the coach scores clarity and specificity against the lesson rubric.
              </p>
            </div>

            {saved ? (
              <div className="actions actions--split">
                <span className="status-line">
                  <StarIcon size={20} fill="#FFC83D" />
                  Saved to your Freelancer Profile · +40 XP
                </span>
                <Link className="btn btn--primary" href="/">
                  Back to roadmap
                </Link>
              </div>
            ) : (
              <div className="actions">
                <button type="button" className="btn btn--primary" disabled={!canSave} onClick={save}>
                  Save headline
                </button>
                {!canSave && <span className="hint hint--error">Keep it between 1 and {LIMIT} characters to save.</span>}
              </div>
            )}
          </div>
        </div>

        <aside className="lesson__side" aria-label="Your profile and preview">
          <div className="side-card">
            <h2 className="cap muted">From your Freelancer Profile</h2>
            <dl className="facts">
              <div>
                <dt>Service</dt>
                <dd>Landing page design</dd>
              </div>
              <div>
                <dt>Target client</dt>
                <dd>B2B SaaS startups</dd>
              </div>
              <div>
                <dt>Proof</dt>
                <dd>
                  1 shipped redesign <span>(self-reported)</span>
                </dd>
              </div>
            </dl>
            <p className="hint">Set in Level 1. Change it there and every channel draft updates.</p>
          </div>

          <div className="side-card side-card--tint">
            <h2 className="cap">Live preview</h2>
            <div className="preview">
              <span className="preview__avatar" aria-hidden="true" />
              <div className="preview__text">
                <span className="preview__name">[Your name]</span>
                <span className="preview__headline">{draft || "Your headline appears here"}</span>
              </div>
            </div>
            <p className="hint" style={{ color: "var(--ink-2)" }}>
              Later reused for your Upwork title and your portfolio page. You paste it into LinkedIn yourself.
            </p>
          </div>
        </aside>
      </main>
    </div>
  );
}
