"use client";

import { useState } from "react";
import { CheckIcon, FlameIcon, StarIcon } from "@/components/icons";
import { ActionView, type Submit } from "@/components/lessons/actions";
import { Modal } from "@/components/ui/Modal";
import { usePlatform } from "@/components/platform/PlatformShell";
import { useDaily, useSubmitDaily } from "@/lib/api/hooks";
import type { DailySubmitResult } from "@/lib/api/types";

/** Today's two-minute challenge. One per local day; finishing it pays XP once and keeps the streak. */
export function DailyCard() {
  const daily = useDaily(true);
  const submit = useSubmitDaily();
  const { showProgress } = usePlatform();
  const [open, setOpen] = useState(false);

  // What finishing today's challenge paid. Kept here so it stays on screen after the query refreshes.
  const [earned, setEarned] = useState<DailySubmitResult | null>(null);

  const data = daily.data;
  if (!data?.challenge) return null;
  const { challenge, completed, streak } = data;
  const review = challenge.action.type === "quiz" ? challenge.action.state.result.review?.[0] : undefined;
  // Counted tasks ("write to 5 clients") show how far along the learner is.
  const tally =
    challenge.action.type === "external_task"
      ? { count: challenge.action.state.payload.count ?? 0, target: challenge.action.config.target_count }
      : null;
  const begun = !!tally && tally.count > 0;

  const close = () => {
    setOpen(false);
    if (earned) {
      showProgress(earned.xp_total, earned.rank);
      setEarned(null);
    }
  };

  const submitOnce: Submit = {
    ...submit,
    mutate: (input) => submit.mutate(input, { onSuccess: (result) => result.xp_awarded > 0 && setEarned(result) }),
  };

  return (
    <>
      <div className={`daily t-orange${completed ? " is-done" : ""}`} data-tour="daily-challenge">
        <span className="daily__icon" aria-hidden="true">
          {completed ? <CheckIcon size={20} /> : <FlameIcon size={24} />}
        </span>
        <div className="daily__text">
          <span className="cap">Today&apos;s challenge{completed ? " · done" : ` · +${challenge.xp} XP`}</span>
          <span className="daily__title">{challenge.title}</span>
          <span className="next-card__meta">
            {completed
              ? `${streak.current}-day streak. Come back tomorrow for the next one.`
              : begun
                ? `${tally.count} of ${tally.target} done. Keep going.`
                : streak.current > 0
                  ? `Keep your ${streak.current}-day streak going.`
                  : "Finish it today to start a streak."}
          </span>
        </div>
        {!completed && (
          <button type="button" className="btn btn--sm btn--primary" onClick={() => setOpen(true)}>
            {begun ? "Continue" : "Open"}
          </button>
        )}
      </div>

      {open && (
        <Modal labelledBy="daily-title" theme="orange" onClose={close}>
          <span className="cap modal__eyebrow">Today&apos;s challenge</span>
          <h2 id="daily-title" className="modal__title">
            {challenge.title}
          </h2>
          {challenge.intro && <p className="card__intro">{challenge.intro}</p>}
          {/* Once done, the challenge is closed for the day: show the outcome, not the form. */}
          {!completed && (
            <div className="daily__action">
              <ActionView action={challenge.action} submit={submitOnce} waitingFor={[]} aiAvailable={false} bare />
            </div>
          )}
          {!completed && (
            <button type="button" className="link-btn" onClick={close}>
              I&apos;ll come back to this
            </button>
          )}
          {completed && review?.explanation && <p className="card__intro">{review.explanation}</p>}
          {completed && (
            <>
              <div className="pills reward__pills">
                {earned && (
                  <span className="pill pill--xp reward__xp">
                    <StarIcon />+{earned.xp_awarded} XP
                  </span>
                )}
                <span className="pill pill--streak">
                  <FlameIcon />
                  {streak.current}-day streak
                </span>
              </div>
              {earned?.rank_up && (
                <p className="reward__rank">
                  Rank up! You are now <strong>{earned.rank.title}</strong>.
                </p>
              )}
              <button type="button" className="btn btn--primary" onClick={close}>
                Close
              </button>
            </>
          )}
        </Modal>
      )}
    </>
  );
}
