"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { DailyCard } from "@/components/daily/DailyCard";
import { usePlatform } from "@/components/platform/PlatformShell";
import { Hero } from "@/components/roadmap/Hero";
import { RoadmapMap } from "@/components/roadmap/RoadmapMap";
import { StepDrawer } from "@/components/roadmap/StepDrawer";
import { TopBar } from "@/components/roadmap/TopBar";
import { track } from "@/lib/analytics";
import { useTourEvent } from "@/lib/api/hooks";
import { flattenSteps, lessonHref } from "@/lib/roadmap";
import { useIsWide } from "@/lib/useIsWide";

/**
 * The journey map. Renders the state the backend computed; it decides nothing about progress.
 * `undefined` for the open step means "not chosen yet": on a wide screen the drawer then opens on the
 * current step, on a phone it stays closed so it does not cover the map.
 */
export function JourneyScreen() {
  const { journey } = usePlatform();
  const router = useRouter();
  const isWide = useIsWide();
  const tourEvent = useTourEvent();
  const [chosen, setChosen] = useState<string | null | undefined>(undefined);

  const steps = useMemo(() => flattenSteps(journey.chapters), [journey.chapters]);
  const current = steps.find((entry) => entry.step.status === "current") ?? null;
  const selectedId = chosen === undefined ? (isWide ? (current?.step.id ?? null) : null) : chosen;
  const selected = steps.find((entry) => entry.step.id === selectedId) ?? null;

  useEffect(() => {
    track("journey_viewed");
  }, []);

  const tourIntro = journey.tour.status === "active" && journey.tour.stage === "journey_intro";
  const openStep = (stepId: string) => {
    // During the tour's first step, the highlighted checkpoint leads straight into the first lesson.
    if (tourIntro && stepId === journey.first_lesson_id) router.push(lessonHref(stepId));
    else setChosen(stepId);
  };
  const openCurrent = () => setChosen(current?.step.id ?? null);

  return (
    <div className="wrap">
      <TopBar xp={journey.xp_total} rank={journey.rank} streak={journey.streak} avatarKey={journey.profile.avatar_key} />
      <Hero
        levels={journey.chapters}
        current={current}
        total={journey.total_count}
        trackLabel={journey.track_label}
        welcome={journey.welcome}
        // The daily challenge joins the journey once the learner has their character (after lesson one).
        extra={journey.profile.avatar_key ? <DailyCard /> : null}
      />
      <main className="layout">
        <RoadmapMap
          levels={journey.chapters}
          current={current}
          selectedId={selectedId}
          onOpen={openStep}
          moreComing={journey.more_coming}
        />
        {selected && (
          <StepDrawer entry={selected} current={current} onClose={() => setChosen(null)} onGoToCurrent={openCurrent} />
        )}
      </main>
      {journey.tour.status !== "active" && (
        <p className="page-foot">
          <button type="button" className="link-btn" onClick={() => tourEvent.mutate("replay")}>
            Replay the guided tour
          </button>
        </p>
      )}
    </div>
  );
}
