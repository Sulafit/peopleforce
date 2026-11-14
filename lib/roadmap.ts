import data from "@/data/roadmap.json";

export type Theme = "yellow" | "blue" | "violet" | "green" | "orange" | "pink";
export type PartKind = "Read" | "Practice" | "Create";

export interface StepPart {
  kind: PartKind;
  title: string;
  minutes: number;
}

export interface Step {
  id: string;
  title: string;
  minutes: number;
  xp: number;
  summary: string;
  parts: StepPart[];
  /** The artifact the learner has at the end of the step. */
  output: string;
}

export interface Level {
  id: string;
  theme: Theme;
  tier: string;
  title: string;
  blurb: string;
  steps: Step[];
}

/** A step together with where it sits in the roadmap. */
export interface StepEntry {
  level: Level;
  levelIndex: number;
  step: Step;
  stepIndex: number;
}

export type StepStatus = "done" | "current" | "locked";

export const LEVELS = data.levels as Level[];

export const STEPS: StepEntry[] = LEVELS.flatMap((level, levelIndex) =>
  level.steps.map((step, stepIndex) => ({ level, levelIndex, step, stepIndex })),
);

/** Demo seed so the map opens mid-journey. A real account starts with []. */
export const DEMO_DONE: string[] = ["l1s1", "l1s2", "l1s3", "l1s4", "l2s1"];

/** Steps that have a lesson page built. */
export const LESSON_ROUTES: Record<string, string> = {
  l2s2: "/lessons/write-your-headline",
};

/** The first unfinished step, or null when the whole roadmap is done. */
export function currentStep(done: ReadonlySet<string>): StepEntry | null {
  return STEPS.find((entry) => !done.has(entry.step.id)) ?? null;
}

export function stepStatus(stepId: string, done: ReadonlySet<string>, current: StepEntry | null): StepStatus {
  if (done.has(stepId)) return "done";
  return current?.step.id === stepId ? "current" : "locked";
}

export function totalXp(done: ReadonlySet<string>): number {
  return STEPS.reduce((sum, entry) => sum + (done.has(entry.step.id) ? entry.step.xp : 0), 0);
}

/**
 * Where each step sits across the road: 0 is the centre, 1 or -1 is one swing to the side.
 * Every level starts and ends at the centre, so the road passes straight through the level signs.
 * Odd levels bulge right, even levels bulge left.
 */
export function roadShape(stepCount: number, levelIndex: number): number[] {
  const direction = levelIndex % 2 === 0 ? 1 : -1;
  const shape = stepCount === 4 ? [0, 1, 1, 0] : stepCount === 3 ? [0, 1, 0] : Array<number>(stepCount).fill(0);
  return shape.map((k) => k * direction);
}
