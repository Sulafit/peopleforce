"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowIcon, StarIcon } from "@/components/icons";
import { ActionView } from "@/components/lessons/actions";
import { BlockView } from "@/components/lessons/blocks";
import { usePlatform } from "@/components/platform/PlatformShell";
import { track } from "@/lib/analytics";
import { isApiError } from "@/lib/api/client";
import { useCompleteLesson, useLesson, useSubmitAction } from "@/lib/api/hooks";
import type { Block, Lesson, LessonAction } from "@/lib/api/types";
import { lessonHref } from "@/lib/roadmap";

/** One screen of the lesson: either a piece of content or a single action. */
type Page =
  | { id: string; kind: "content"; block: Block }
  | { id: string; kind: "action"; action: LessonAction; heading: string | null; intro: string | null };

/** Lessons are played one step at a time: every content block and every action gets its own screen. */
function buildPages(lesson: Lesson): Page[] {
  const actions = Object.fromEntries(lesson.actions.map((action) => [action.key, action]));
  return lesson.blocks.flatMap((block): Page[] => {
    if (!("action_keys" in block)) return [{ id: block.key, kind: "content", block }];
    return block.action_keys
      .map((key) => actions[key])
      .filter((action): action is LessonAction => !!action)
      .map((action, index) => ({
        id: `${block.key}:${action.key}`,
        kind: "action",
        action,
        heading: block.title,
        intro: index === 0 ? block.intro : null,
      }));
  });
}

/** Where to reopen a lesson: at the first required step still open, if the learner already began. */
function resumeIndex(lesson: Lesson, pages: Page[]): number {
  const began = lesson.actions.some((action) => action.state.updated_at !== null);
  if (!began || lesson.progress_status === "completed") return 0;
  const open = pages.findIndex((page) => page.kind === "action" && page.action.required && !page.action.state.completed);
  return open === -1 ? pages.length - 1 : open;
}

export function LessonScreen() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const { showReward } = usePlatform();
  const lesson = useLesson(lessonId);
  const submit = useSubmitAction(lessonId);
  const complete = useCompleteLesson(lessonId);
  const [chosen, setChosen] = useState<number | null>(null);

  useEffect(() => {
    track("lesson_viewed", { lesson_id: lessonId });
  }, [lessonId]);

  const data = lesson.data;
  const pages = useMemo(() => (data ? buildPages(data) : []), [data]);

  if (!data) {
    const error = lesson.error;
    return (
      <div className="wrap">
        <div className="screen-note" role="status">
          {error ? (
            <>
              <p>
                {isApiError(error, "lesson_locked")
                  ? "This lesson is still locked. Finish your current lesson to open it."
                  : isApiError(error, "lesson_unavailable") || isApiError(error, "not_found")
                    ? "This lesson is coming soon."
                    : error.message}
              </p>
              <Link className="btn" href="/journey">
                <ArrowIcon back />
                Back to your journey
              </Link>
            </>
          ) : (
            <p>Opening your lesson…</p>
          )}
        </div>
      </div>
    );
  }

  const index = Math.min(chosen ?? resumeIndex(data, pages), pages.length - 1);
  const page = pages[index];
  const last = index === pages.length - 1;
  const titles = Object.fromEntries(data.actions.map((action) => [action.key, action.title]));
  const finished = data.progress_status === "completed";
  const rewardPending = data.progress_status === "reward_pending";
  // A required action has to be done before moving on; an optional one can be skipped.
  const action = page.kind === "action" ? page.action : null;
  const blocked = !!action && action.required && !action.state.completed;
  const skippable = !!action && !action.required && !action.state.completed;

  const finish = () =>
    complete.mutate(undefined, {
      // A paid reward is celebrated here; a pending one (first lesson) opens the avatar picker via the shell.
      onSuccess: (result) => result.status === "completed" && result.reward && !result.already_completed && showReward(result.reward),
    });

  return (
    <div className={`wrap wrap--lesson t-${data.chapter.theme}`}>
      <header className="lesson-bar">
        <Link className="icon-btn" href="/journey" aria-label="Back to your journey">
          <ArrowIcon back />
        </Link>
        <div
          className="progress"
          role="progressbar"
          aria-label="Lesson progress"
          aria-valuemin={0}
          aria-valuemax={pages.length}
          aria-valuenow={index + 1}
        >
          <div className="progress__fill" style={{ width: `${((index + (finished ? 1 : 0)) / pages.length) * 100}%` }} />
        </div>
        <span className="pill pill--sm pill--xp">
          <StarIcon size={14} />+{data.xp} XP
        </span>
      </header>

      <main className="lesson-step" data-tour="lesson-step">
        <p className="cap lesson-step__eyebrow">
          {data.title} · Step {index + 1} of {pages.length}
        </p>

        {index === 0 && (
          <div className="lesson__intro">
            <h1>{data.title}</h1>
            <p>{data.summary}</p>
          </div>
        )}

        {/* Keyed by page so each step animates in and local form state belongs to its step. */}
        <div key={`${data.content_version}-${page.id}`} className="lesson-step__body">
          {page.kind === "content" ? (
            <BlockView block={page.block} renderActions={() => null} />
          ) : (
            <section className="card">
              {page.heading && <span className="cap muted">{page.heading}</span>}
              {page.intro && <p className="card__intro">{page.intro}</p>}
              <ActionView
                action={page.action}
                submit={submit}
                waitingFor={page.action.blocked_by.map((key) => titles[key] ?? key)}
                aiAvailable={data.ai_available}
              />
            </section>
          )}
        </div>

        {last && rewardPending && <p className="status-line">Your work is saved. Choose your character to claim your reward.</p>}
        {last && finished && (
          <p className="status-line">
            <StarIcon size={20} fill="#FFC83D" />
            Completed · +{data.xp} XP
          </p>
        )}
        {complete.isError && (
          <p className="hint hint--error" role="alert">
            {complete.error.message}
          </p>
        )}

        <nav className="lesson-nav" aria-label="Lesson steps">
          <button type="button" className="btn" disabled={index === 0} onClick={() => setChosen(index - 1)}>
            <ArrowIcon back />
            Back
          </button>
          {!last ? (
            <button type="button" className="btn btn--primary" disabled={blocked} onClick={() => setChosen(index + 1)}>
              {skippable ? "Skip" : "Continue"}
              <ArrowIcon />
            </button>
          ) : finished ? (
            data.next_lesson?.playable ? (
              <Link className="btn btn--primary" href={lessonHref(data.next_lesson.id)}>
                Next lesson
                <ArrowIcon />
              </Link>
            ) : (
              <Link className="btn btn--primary" href="/journey">
                Back to your journey
              </Link>
            )
          ) : (
            !rewardPending && (
              <button type="button" className="btn btn--primary" disabled={!data.completable || complete.isPending} onClick={finish}>
                {complete.isPending ? "Finishing…" : "Finish lesson"}
              </button>
            )
          )}
        </nav>
        {last && !finished && !rewardPending && !data.completable && data.missing_required.length > 0 && (
          <p className="hint lesson-nav__hint">Still to do: {data.missing_required.map((key) => titles[key] ?? key).join(", ")}.</p>
        )}
      </main>
    </div>
  );
}
