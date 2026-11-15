"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, use, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { AvatarPicker } from "@/components/avatar/AvatarPicker";
import { Celebration } from "@/components/rewards/Celebration";
import { ProgressToast, type ProgressSnapshot } from "@/components/rewards/ProgressToast";
import { FirstRunTour } from "@/components/tour/FirstRunTour";
import { FIRST_RUN_STEPS } from "@/components/tour/steps";
import { identify } from "@/lib/analytics";
import { isApiError } from "@/lib/api/client";
import { useJourney, useMe, useSetTimezone, useTourEvent } from "@/lib/api/hooks";
import type { Journey, Rank, Reward } from "@/lib/api/types";

interface PlatformContextValue {
  journey: Journey;
  /** Show the completion celebration for a reward the server just paid. */
  showReward: (reward: Reward) => void;
  /** Show the small "XP so far" note (after a reward has been acknowledged). */
  showProgress: (xpTotal: number, rank: Rank) => void;
}

const PlatformContext = createContext<PlatformContextValue | null>(null);

export function usePlatform(): PlatformContextValue {
  const value = use(PlatformContext);
  if (!value) throw new Error("usePlatform must be used inside PlatformShell");
  return value;
}

/**
 * Wraps every signed-in screen. Owns three things that span routes:
 *  - the auth guard (401 -> /login, account without a quiz -> /start),
 *  - the reward sequence (avatar picker while a reward is pending, then the celebration),
 *  - the first-run tour.
 * All of it is derived from the journey the server returns, so a refresh or a new device resumes
 * exactly where the learner left off.
 */
export function PlatformShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const journey = useJourney();
  const me = useMe();
  const tourEvent = useTourEvent();
  const [localReward, setLocalReward] = useState<Reward | null>(null);

  const error = journey.error;
  useEffect(() => {
    if (isApiError(error, "unauthorized")) router.replace("/login");
    else if (isApiError(error, "onboarding_required")) router.replace("/start");
  }, [error, router]);

  const userId = me.data?.id;
  useEffect(() => {
    if (userId) identify(userId);
  }, [userId]);

  // Streaks and the daily challenge follow the learner's own day, so tell the server the time zone.
  const setTimezone = useSetTimezone();
  const { mutate: saveTimezone } = setTimezone;
  const savedZone = journey.data?.profile.timezone;
  useEffect(() => {
    if (!savedZone) return;
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zone && zone !== savedZone) saveTimezone(zone, { onSuccess: () => journey.refetch() });
    // Only when the stored zone changes; `journey.refetch` is stable enough to leave out.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedZone, saveTimezone]);

  const [progress, setProgress] = useState<ProgressSnapshot | null>(null);
  const showReward = useCallback((reward: Reward) => setLocalReward(reward), []);
  const showProgress = useCallback(
    (xpTotal: number, rank: Rank) => setProgress((old) => ({ xpTotal, rank, id: (old?.id ?? 0) + 1 })),
    [],
  );
  const dismissProgress = useCallback(() => setProgress(null), []);
  const data = journey.data;
  const context = useMemo(
    () => (data ? { journey: data, showReward, showProgress } : null),
    [data, showReward, showProgress],
  );

  if (!data || !context) {
    const redirecting = isApiError(error, "unauthorized") || isApiError(error, "onboarding_required");
    return (
      <div className="wrap">
        <div className="screen-note" role="status">
          {error && !redirecting ? (
            <>
              <p>{error.message}</p>
              <button type="button" className="btn" onClick={() => journey.refetch()}>
                Try again
              </button>
            </>
          ) : (
            <p>Loading your journey…</p>
          )}
        </div>
      </div>
    );
  }

  const tourActive = data.tour.status === "active";
  const pendingAvatar = data.pending_reward_lesson_id !== null;
  // A reward paid in this tab, or (first-run tour only) the one the server says is still unacknowledged.
  const reward = pendingAvatar ? null : (localReward ?? data.last_reward);
  const firstReward = tourActive && data.tour.stage === "first_reward_claimed";

  const closeReward = () => {
    if (reward) showProgress(reward.xp_total, reward.rank);
    setLocalReward(null);
    if (firstReward) tourEvent.mutate("reward_acknowledged");
    if (pathname !== "/journey") router.push("/journey");
  };

  return (
    <PlatformContext value={context}>
      {children}
      <FirstRunTour journey={data} blocked={pendingAvatar || reward !== null} />
      {pendingAvatar && (
        <AvatarPicker
          avatars={data.avatars}
          message={tourActive ? FIRST_RUN_STEPS.avatar_selection.message : "Choose a character to accompany you on your journey."}
          onSelected={(result) => result.reward && setLocalReward(result.reward)}
        />
      )}
      {reward && (
        <Celebration
          reward={reward}
          avatarKey={data.profile.avatar_key}
          message={firstReward ? FIRST_RUN_STEPS.first_reward_claimed.message : "Lesson complete. Nice work."}
          onContinue={closeReward}
        />
      )}
      {progress && !reward && !pendingAvatar && <ProgressToast snapshot={progress} onDismiss={dismissProgress} />}
    </PlatformContext>
  );
}
