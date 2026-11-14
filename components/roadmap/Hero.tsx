import { ArrowIcon } from "@/components/icons";
import { LEVELS, type StepEntry } from "@/lib/roadmap";

interface HeroProps {
  done: ReadonlySet<string>;
  current: StepEntry | null;
  total: number;
  onContinue: () => void;
}

export function Hero({ done, current, total, onContinue }: HeroProps) {
  const currentLevel = current ? current.levelIndex : LEVELS.length;

  return (
    <section className="hero">
      <div className="hero__text">
        <span className="cap muted">Your roadmap · Web designer track</span>
        <h1>Build a client-ready freelance presence</h1>
        <p className="hero__lead">
          One road, six levels, {total} steps. Each step is a little harder than the last and ends with something you can
          use: a résumé, a profile, a published page, a practiced reply.
        </p>
        {current ? (
          <div className={`next-card t-${current.level.theme}`}>
            <div className="next-card__text">
              <span className="cap">Next up · Level {current.levelIndex + 1}</span>
              <span className="next-card__title">{current.step.title}</span>
              <span className="next-card__meta">
                {current.level.title} · {current.step.minutes} min · +{current.step.xp} XP
              </span>
            </div>
            <button type="button" className="btn btn--primary" onClick={onContinue}>
              Continue
              <ArrowIcon />
            </button>
          </div>
        ) : (
          <p className="next-card__title">All {total} steps complete.</p>
        )}
      </div>

      {/* Progress tower: one slab per level, solid once the level is started */}
      <div className="tower" aria-hidden="true">
        {LEVELS.map((level, index) => {
          const started = level.steps.some((step) => done.has(step.id));
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
