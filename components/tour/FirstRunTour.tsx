"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FIRST_RUN_STEPS } from "@/components/tour/steps";
import { useTourHighlight } from "@/components/tour/useTourHighlight";
import { track } from "@/lib/analytics";
import { useTourEvent } from "@/lib/api/hooks";
import type { Journey } from "@/lib/api/types";
import { flattenSteps, lessonHref } from "@/lib/roadmap";

/**
 * Route-aware orchestration of the first-run tour. Reads the persisted stage, decides whether the
 * current screen has something to highlight, and turns the learner's choice into a semantic event.
 * Dialog stages (avatar, reward) are rendered by PlatformShell; this component handles highlights.
 */
export function FirstRunTour({ journey, blocked }: { journey: Journey; blocked: boolean }) {
  const pathname = usePathname();
  const router = useRouter();
  const tourEvent = useTourEvent();
  // "Got it" on the lesson hint is a view-only acknowledgement; remember it for this tab.
  const [lessonHintSeen, setLessonHintSeen] = useState(false);

  const { stage, status } = journey.tour;
  const step = stage === "completed" ? null : FIRST_RUN_STEPS[stage];
  const onJourney = pathname === "/journey";
  const onFirstLesson = pathname === lessonHref(journey.first_lesson_id);
  const current = flattenSteps(journey.chapters).find((entry) => entry.step.status === "current") ?? null;

  const visible =
    status === "active" &&
    !blocked &&
    !!step &&
    ((step.screen === "journey" && onJourney && !!current) ||
      (step.screen === "lesson" && onFirstLesson && !lessonHintSeen));

  useEffect(() => {
    if (visible) track("tour_step_viewed", { stage });
  }, [visible, stage]);

  useTourHighlight({
    active: visible,
    anchor: step?.anchor ?? "",
    title: step?.title ?? "",
    message: step?.message ?? "",
    actionLabel: step?.actionLabel ?? "OK",
    onAction: () => {
      if (stage === "journey_intro") {
        router.push(lessonHref(journey.first_lesson_id));
      } else if (stage === "first_lesson_started") {
        setLessonHintSeen(true);
      } else if (stage === "next_lesson_prompt") {
        tourEvent.mutate("next_prompt_acknowledged");
        if (current?.step.playable) router.push(lessonHref(current.step.id));
      }
    },
    onDismiss: () => {
      if (stage === "first_lesson_started") setLessonHintSeen(true);
      // Closing the last hint is an acknowledgement; closing an earlier one skips the tour.
      else tourEvent.mutate(stage === "next_lesson_prompt" ? "next_prompt_acknowledged" : "skip");
    },
  });

  return null;
}
