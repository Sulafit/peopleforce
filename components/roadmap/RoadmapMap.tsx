import { FlagIcon, LockIcon } from "@/components/icons";
import { StepNode } from "@/components/roadmap/StepNode";
import { LEVELS, roadShape, stepStatus, type StepEntry } from "@/lib/roadmap";

interface RoadmapMapProps {
  done: ReadonlySet<string>;
  current: StepEntry | null;
  selectedId: string | null;
  onOpen: (stepId: string) => void;
  onReset: () => void;
}

/** The map: one outlined strip, one tinted zone per level, one road through all of them. */
export function RoadmapMap({ done, current, selectedId, onOpen, onReset }: RoadmapMapProps) {
  const currentLevel = current ? current.levelIndex : LEVELS.length;

  return (
    <div className="map">
      {LEVELS.map((level, levelIndex) => {
        const count = level.steps.length;
        const doneCount = level.steps.filter((step) => done.has(step.id)).length;
        const levelDone = doneCount === count;
        const locked = levelIndex > currentLevel;
        const reached = levelIndex <= currentLevel;
        const xs = roadShape(count, levelIndex);
        const direction = levelIndex % 2 === 0 ? 1 : -1;

        return (
          <section
            key={level.id}
            className={`zone zone--${levelIndex + 1} t-${level.theme}`}
            aria-label={`Level ${levelIndex + 1}: ${level.title}`}
          >
            <div className="gate">
              <span
                className={`gate-line${levelIndex === 0 ? " gate-line--first" : ""}${reached ? " is-on" : ""}`}
                aria-hidden="true"
              />
              <div className={`sign ${levelIndex % 2 === 0 ? "sign--tl" : "sign--tr"}`}>
                <span className="sign__badge" aria-hidden="true">
                  {levelIndex + 1}
                </span>
                <div className="sign__body">
                  <div className="sign__head">
                    <span className="cap">
                      Level {levelIndex + 1} · {level.tier}
                    </span>
                    <span className="chip">
                      {levelDone ? (
                        `Done · ${count} of ${count}`
                      ) : locked ? (
                        <>
                          <LockIcon size={11} />
                          Locked
                        </>
                      ) : (
                        `${doneCount} of ${count} steps`
                      )}
                    </span>
                  </div>
                  <h2 className="sign__title">{level.title}</h2>
                  <p className="sign__blurb">{level.blurb}</p>
                </div>
              </div>
            </div>

            {level.steps.map((step, stepIndex) => {
              const next = level.steps[stepIndex + 1];
              const x = xs[stepIndex];
              const status = stepStatus(step.id, done, current);
              return (
                <StepNode
                  key={step.id}
                  step={step}
                  number={stepIndex + 1}
                  status={status}
                  selected={selectedId === step.id}
                  x={x}
                  // Labels go on the outside of the bend; centre steps use the side the road bends away from.
                  labelSide={x !== 0 ? x : -direction}
                  toNext={next ? xs[stepIndex + 1] - x : null}
                  // The stretch to the next step is travelled once this step is done.
                  travelled={status === "done" && !!next && stepStatus(next.id, done, current) !== "locked"}
                  stubTop={stepIndex === 0 ? (reached ? "on" : "off") : null}
                  stubBottom={!next ? (levelDone ? "on" : "off") : null}
                  onOpen={onOpen}
                />
              );
            })}

            {levelIndex === LEVELS.length - 1 && (
              <div className="fin">
                <span className={`fin-line${current ? "" : " is-on"}`} aria-hidden="true" />
                <span className="fin-badge" aria-hidden="true">
                  <FlagIcon />
                </span>
                <div className="fin-text">
                  <strong>Finish</strong>
                  <span>A client-ready freelance presence</span>
                </div>
                <button type="button" className="reset" onClick={onReset}>
                  Reset demo progress
                </button>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
