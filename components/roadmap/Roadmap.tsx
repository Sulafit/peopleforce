"use client";

import { useState } from "react";
import { Hero } from "@/components/roadmap/Hero";
import { RoadmapMap } from "@/components/roadmap/RoadmapMap";
import { StepDrawer } from "@/components/roadmap/StepDrawer";
import { TopBar } from "@/components/roadmap/TopBar";
import { useIsWide, useProgress } from "@/lib/progress";
import { STEPS, currentStep, totalXp } from "@/lib/roadmap";

/**
 * The roadmap page. All state lives here: the finished steps (persisted) and the open step.
 * `undefined` for the open step means "not chosen yet": on a wide screen the drawer then
 * opens on the current step, on a phone it stays closed so it does not cover the map.
 */
export function Roadmap() {
  const { done, markDone, reset } = useProgress();
  const isWide = useIsWide();
  const [chosen, setChosen] = useState<string | null | undefined>(undefined);

  const current = currentStep(done);
  const selectedId = chosen === undefined ? (isWide ? (current?.step.id ?? null) : null) : chosen;
  const selected = STEPS.find((entry) => entry.step.id === selectedId) ?? null;

  const openCurrent = () => setChosen(current?.step.id ?? null);

  const completeCurrent = () => {
    if (!current) return;
    markDone(current.step.id);
    const next = STEPS[STEPS.indexOf(current) + 1];
    setChosen(next ? next.step.id : current.step.id);
  };

  return (
    <div className="wrap">
      <TopBar doneCount={STEPS.filter((entry) => done.has(entry.step.id)).length} total={STEPS.length} xp={totalXp(done)} />
      <Hero done={done} current={current} total={STEPS.length} onContinue={openCurrent} />
      <main className="layout">
        <RoadmapMap
          done={done}
          current={current}
          selectedId={selectedId}
          onOpen={setChosen}
          onReset={() => {
            reset();
            setChosen(undefined);
          }}
        />
        {selected && (
          <StepDrawer
            entry={selected}
            done={done}
            current={current}
            onClose={() => setChosen(null)}
            onComplete={completeCurrent}
            onGoToCurrent={openCurrent}
          />
        )}
      </main>
    </div>
  );
}
