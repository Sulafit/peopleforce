import type { Chapter, LessonNode } from "@/lib/api/types";

export type Theme = "yellow" | "blue" | "violet" | "green" | "orange" | "pink";
export type PartKind = "Read" | "Practice" | "Create";
export type StepStatus = "done" | "current" | "locked";

/** A lesson together with where it sits on the journey map. Statuses come from the backend. */
export interface StepEntry {
  level: Chapter;
  levelIndex: number;
  step: LessonNode;
  stepIndex: number;
}

export function flattenSteps(chapters: Chapter[]): StepEntry[] {
  return chapters.flatMap((level, levelIndex) =>
    level.lessons.map((step, stepIndex) => ({ level, levelIndex, step, stepIndex })),
  );
}

export function lessonHref(lessonId: string): string {
  return `/journey/lessons/${lessonId}`;
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
