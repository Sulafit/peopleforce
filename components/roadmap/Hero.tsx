import Link from "next/link";
import { ArrowIcon } from "@/components/icons";
import type { Chapter } from "@/lib/api/types";
import { lessonHref, type StepEntry } from "@/lib/roadmap";

interface HeroProps {
  levels: Chapter[];
  current: StepEntry | null;
  total: number;
  trackLabel: string;
  welcome: string;
  /** Optional card shown under "Next up" (the daily challenge). */
  extra?: React.ReactNode;
}

export function Hero({ levels, current, total, trackLabel, welcome, extra }: HeroProps) {
  const currentLevel = current ? current.levelIndex : levels.length;

  return (
    <section className="hero">
      <div className="hero__text">
        <span className="cap muted">Your journey · {trackLabel}</span>
        <h1>{welcome}</h1>
        <p className="hero__lead">
          Each step ends with something you can use: an offer, a bio, a published page, a practiced reply. New levels
          are added as they are ready.
        </p>
        {current ? (
          <div className={`next-card t-${current.level.theme}`}>
            <div className="next-card__text">
              <span className="cap">Next up · Level {current.levelIndex + 1}</span>
              <span className="next-card__title">{current.step.title}</span>
              <span className="next-card__meta">
                {current.level.title} ·{" "}
                {current.step.playable ? `${current.step.minutes} min · +${current.step.xp} XP` : "Coming soon"}
              </span>
            </div>
            {current.step.playable ? (
              // Says what it does and does it: straight into the lesson.
              <Link className="btn btn--primary" href={lessonHref(current.step.id)}>
                {current.step.reward_pending ? "Claim your reward" : current.step.started ? "Continue lesson" : "Start lesson"}
                <ArrowIcon />
              </Link>
            ) : (
              <button type="button" className="btn" disabled>
                Coming soon
              </button>
            )}
          </div>
        ) : (
          <p className="next-card__title">All {total} published steps complete. More are on the way.</p>
        )}
        {extra}
      </div>

      {/* Progress tower: one slab per level, solid once the level is started */}
      <div className="tower" aria-hidden="true">
        {levels.map((level, index) => {
          const started = level.lessons.some((step) => step.status === "done");
          return (
            <div
              key={level.id}
              className={`slab t-${level.theme} ${started ? "slab--solid" : "slab--ghost"}${index === currentLevel ? " slab--float" : ""}`}
            />
          );
        })}
      </div>
    </section>
  );
}
