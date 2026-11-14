import { StarIcon } from "@/components/icons";
import type { Step, StepStatus } from "@/lib/roadmap";

interface StepNodeProps {
  step: Step;
  number: number;
  status: StepStatus;
  selected: boolean;
  /** Position across the road: -1 left, 0 centre, 1 right. */
  x: number;
  /** Which side the label sits on: negative left, positive right. */
  labelSide: number;
  /** Horizontal move to the next step in the level, or null for the last step. */
  toNext: number | null;
  travelled: boolean;
  /** Vertical road pieces that join the step to the level sign above or the zone below. */
  stubTop: "on" | "off" | null;
  stubBottom: "on" | "off" | null;
  onOpen: (stepId: string) => void;
}

const STATUS_LABEL: Record<StepStatus, string> = {
  done: "completed",
  current: "current step",
  locked: "locked",
};

/** One step on the road: an isometric tile, its label and the connector to the next step. */
export function StepNode({ step, number, status, selected, x, labelSide, toNext, travelled, stubTop, stubBottom, onOpen }: StepNodeProps) {
  const position = x === 0 ? "x0" : x > 0 ? "xp" : "xn";
  const segment = toNext === null ? null : toNext === 0 ? "v" : toNext > 0 ? "r" : "l";

  return (
    <div className="row">
      {stubTop && <span className={`stub stub--top${stubTop === "on" ? " is-on" : ""}`} aria-hidden="true" />}
      {stubBottom && <span className={`stub stub--bot${stubBottom === "on" ? " is-on" : ""}`} aria-hidden="true" />}
      <button
        type="button"
        className={`node node--${position} is-${status}${selected ? " is-selected" : ""}`}
        aria-label={`Step ${number}: ${step.title}, ${step.minutes} minutes, ${STATUS_LABEL[status]}`}
        aria-pressed={selected}
        onClick={() => onOpen(step.id)}
      >
        {segment && <span className={`seg seg--${segment}${travelled ? " is-on" : ""}`} aria-hidden="true" />}
        <span className="tile-wrap">
          <span className="tile">
            <span className="tile__face">{status === "done" ? <StarIcon size={30} /> : number}</span>
          </span>
        </span>
        <span className={`lbl${labelSide > 0 ? "" : " lbl--left"}`}>
          {status === "current" && (
            <span className="here" aria-hidden="true">
              You are here
            </span>
          )}
          <span className="lbl__title">{step.title}</span>
          <span className="lbl__meta">
            {step.minutes} min · +{step.xp} XP
          </span>
        </span>
      </button>
    </div>
  );
}
