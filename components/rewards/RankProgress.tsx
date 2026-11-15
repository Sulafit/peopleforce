"use client";

import { useEffect, useState } from "react";
import type { Rank } from "@/lib/api/types";

/** XP bar toward the next rank. With `gained`, it starts where the learner was and fills to where they are. */
export function RankProgress({ rank, xpTotal, gained = 0, rankUp = false }: { rank: Rank; xpTotal: number; gained?: number; rankUp?: boolean }) {
  const before = rankUp || !rank.xp_span ? 0 : Math.max(0, (rank.xp_into - gained) / rank.xp_span);
  const [progress, setProgress] = useState(gained > 0 ? before : rank.progress);

  useEffect(() => {
    // Next frame, so the browser paints the starting width first and the CSS transition runs.
    const id = requestAnimationFrame(() => setProgress(rank.progress));
    return () => cancelAnimationFrame(id);
  }, [rank.progress]);

  return (
    <div className="rank-progress">
      <div className="rank-bar__labels">
        <span>
          Rank {rank.number} · {rank.title}
        </span>
        <span>{rank.next_title ? `${rank.next_min_xp! - xpTotal} XP to ${rank.next_title}` : "Top rank"}</span>
      </div>
      <div
        className="progress progress--slow"
        role="progressbar"
        aria-label="Progress to the next rank"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(rank.progress * 100)}
      >
        <div className="progress__fill" style={{ width: `${Math.round(progress * 100)}%` }} />
      </div>
    </div>
  );
}
