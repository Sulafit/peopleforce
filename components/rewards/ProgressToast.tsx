"use client";

import { useEffect } from "react";
import { CloseIcon, StarIcon } from "@/components/icons";
import { RankProgress } from "@/components/rewards/RankProgress";
import type { Rank } from "@/lib/api/types";

export interface ProgressSnapshot {
  xpTotal: number;
  rank: Rank;
  /** Changes with every new snapshot, so the same totals shown twice still restart the timer. */
  id: number;
}

const VISIBLE_MS = 7000;

/** A small, self-dismissing note after a reward: where the learner stands overall. */
export function ProgressToast({ snapshot, onDismiss }: { snapshot: ProgressSnapshot; onDismiss: () => void }) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, VISIBLE_MS);
    return () => window.clearTimeout(timer);
  }, [snapshot.id, onDismiss]);

  return (
    <div className="toast t-yellow" role="status">
      <span className="toast__icon" aria-hidden="true">
        <StarIcon size={22} fill="#FFC83D" />
      </span>
      <div className="toast__body">
        <strong className="toast__title">{snapshot.xpTotal} XP so far</strong>
        <RankProgress rank={snapshot.rank} xpTotal={snapshot.xpTotal} />
      </div>
      <button type="button" className="icon-btn icon-btn--sm" aria-label="Dismiss" onClick={onDismiss}>
        <CloseIcon size={14} />
      </button>
    </div>
  );
}
