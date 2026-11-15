import type { TourStage } from "@/lib/api/types";

/**
 * The first-run tour, as data. The backend owns the stage (a persisted state machine); this file only
 * says how each stage is presented and where. Anchors are stable `data-tour` names, never CSS selectors
 * or coordinates.
 *
 *   screen "journey" / "lesson": a Driver.js highlight on the anchor, on that route only.
 *   screen "dialog": the app's own dialog carries the message (avatar picker, reward celebration).
 */
export interface TourStep {
  screen: "journey" | "lesson" | "dialog";
  anchor?: string;
  title: string;
  message: string;
  actionLabel?: string;
}

export const FIRST_RUN_STEPS: Record<Exclude<TourStage, "completed">, TourStep> = {
  journey_intro: {
    screen: "journey",
    anchor: "current-checkpoint",
    title: "Welcome to your journey!",
    message: "Each checkpoint helps you build a real part of your freelance business. Start with your first lesson.",
    actionLabel: "Start first lesson",
  },
  first_lesson_started: {
    screen: "lesson",
    anchor: "lesson-step",
    title: "Learn by doing",
    message: "You'll learn by doing. The work you complete here becomes part of your professional profile.",
    actionLabel: "Got it",
  },
  avatar_selection: {
    screen: "dialog",
    title: "Great start!",
    message: "Great start! Choose a character to accompany you on your journey.",
  },
  first_reward_claimed: {
    screen: "dialog",
    title: "First lesson complete",
    message: "You completed your first lesson and earned your first XP.",
  },
  next_lesson_prompt: {
    screen: "journey",
    anchor: "current-checkpoint",
    title: "Your next lesson is ready",
    message: "Your next lesson is ready. Keep building your freelance presence.",
    actionLabel: "Open next lesson",
  },
};
