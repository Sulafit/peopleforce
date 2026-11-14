import Link from "next/link";
import { ClockIcon, CloseIcon, LockIcon, StarIcon } from "@/components/icons";
import { LESSON_ROUTES, stepStatus, type StepEntry } from "@/lib/roadmap";

interface StepDrawerProps {
  entry: StepEntry;
  done: ReadonlySet<string>;
  current: StepEntry | null;
  onClose: () => void;
  onComplete: () => void;
  onGoToCurrent: () => void;
}

const STATUS_LABEL = { done: "Completed", current: "Current step", locked: "Locked" } as const;

/** What opens when a step is clicked: the course content for that step. */
export function StepDrawer({ entry, done, current, onClose, onComplete, onGoToCurrent }: StepDrawerProps) {
  const { level, levelIndex, step, stepIndex } = entry;
  const status = stepStatus(step.id, done, current);
  const lessonRoute = LESSON_ROUTES[step.id];

  return (
    <aside className={`drawer t-${level.theme}`} aria-label="Step details">
      <div className="drawer__head">
        <span className="pill pill--sm pill--level cap">
          Level {levelIndex + 1} · {level.title}
        </span>
        <button type="button" className="icon-btn" aria-label="Close step details" onClick={onClose}>
          <CloseIcon />
        </button>
      </div>

      <div className="drawer__intro">
        <span className="drawer__status">
          Step {stepIndex + 1} of {level.steps.length} · {STATUS_LABEL[status]}
        </span>
        <h2 className="drawer__title">{step.title}</h2>
        <p className="drawer__summary">{step.summary}</p>
      </div>

      <div className="pills">
        <span className="pill pill--sm">
          <ClockIcon />
          {step.minutes} min
        </span>
        <span className="pill pill--sm pill--xp">
          <StarIcon size={14} />+{step.xp} XP
        </span>
        <span className="pill pill--sm">{level.tier}</span>
      </div>

      <div>
        <h3 className="cap section-label">In this step</h3>
        <ol>
          {step.parts.map((part, index) => (
            <li key={part.title} className="part">
              <span className="part__n">{index + 1}</span>
              <span className="part__text">
                <span className="part__title">{part.title}</span>
                <span className="part__kind">{part.kind}</span>
              </span>
              <span className="part__min">{part.minutes} min</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="outcome">
        <span className="cap">You finish with</span>
        <p>{step.output}</p>
      </div>

      {status === "current" && (
        <div className="actions">
          {lessonRoute ? (
            <Link className="btn btn--primary grow" href={lessonRoute}>
              Start lesson
            </Link>
          ) : (
            <button type="button" className="btn btn--primary grow" disabled title="This lesson page is not built yet">
              Lesson coming soon
            </button>
          )}
          <button type="button" className="btn" onClick={onComplete}>
            Mark as done
          </button>
        </div>
      )}

      {status === "done" && (
        <div className="actions actions--split">
          <span className="status-line">
            <StarIcon size={20} fill="#FFC83D" />
            Completed · +{step.xp} XP
          </span>
        </div>
      )}

      {status === "locked" && (
        <div className="actions actions--stack">
          <p className="locked-note">
            <LockIcon />
            <span>Locked. Finish “{current?.step.title}” first.</span>
          </p>
          <button type="button" className="btn" onClick={onGoToCurrent}>
            Go to current step
          </button>
        </div>
      )}
    </aside>
  );
}
