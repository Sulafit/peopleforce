"use client";

import { Avatar } from "@/components/avatar/avatars";
import { StarIcon } from "@/components/icons";
import { Confetti } from "@/components/rewards/Confetti";
import { RankProgress } from "@/components/rewards/RankProgress";
import { useCountUp } from "@/components/rewards/useCountUp";
import { Modal } from "@/components/ui/Modal";
import type { Reward } from "@/lib/api/types";

interface CelebrationProps {
  reward: Reward;
  avatarKey: string | null;
  message: string;
  onContinue: () => void;
}

/**
 * Completion feedback: confetti, the character on a spinning sunburst, XP counting up, the rank bar
 * filling, achievements, what unlocked. Every number comes from the server; only the motion is local.
 */
export function Celebration({ reward, avatarKey, message, onContinue }: CelebrationProps) {
  const total = useCountUp(reward.xp_total - reward.xp_awarded, reward.xp_total);

  return (
    <>
      <Confetti />
      <Modal labelledBy="reward-title" theme="yellow" onClose={onContinue}>
        <div className="reward__stage" aria-hidden="true">
          <span className="reward__rays" />
          <div className="reward__burst">{avatarKey ? <Avatar avatarKey={avatarKey} size={84} /> : <StarIcon size={64} fill="#FFC83D" />}</div>
          {reward.xp_awarded > 0 && <span className="reward__float">+{reward.xp_awarded} XP</span>}
          {[0, 1, 2, 3].map((index) => (
            <span key={index} className={`reward__spark reward__spark--${index}`}>
              <StarIcon size={index % 2 ? 16 : 22} fill="#FFC83D" />
            </span>
          ))}
        </div>
        <span className="cap modal__eyebrow">{reward.lesson_title}</span>
        <h2 id="reward-title" className="modal__title">
          {message}
        </h2>
        <div className="pills reward__pills">
          {reward.xp_awarded > 0 && (
            <span className="pill pill--xp reward__xp">
              <StarIcon />+{reward.xp_awarded} XP
            </span>
          )}
          {/* The visible number counts up; assistive tech gets the final value once. */}
          <span className="pill" aria-label={`${reward.xp_total} XP total`}>
            <span aria-hidden="true">{total} XP total</span>
          </span>
        </div>
        <RankProgress rank={reward.rank} xpTotal={reward.xp_total} gained={reward.xp_awarded} rankUp={reward.rank_up} />
        {reward.rank_up && (
          <p className="reward__rank reward__rank--up">
            Rank up! You are now <strong>{reward.rank.title}</strong>.
          </p>
        )}
        {reward.achievements.length > 0 && (
          <ul className="reward__achievements">
            {reward.achievements.map((achievement) => (
              <li key={achievement.key} className="outcome">
                <span className="cap">Achievement unlocked</span>
                <p>
                  {achievement.title} <span className="muted">· {achievement.description}</span>
                </p>
              </li>
            ))}
          </ul>
        )}
        {reward.next_lesson && (
          <p className="reward__next">
            Unlocked next: <strong>{reward.next_lesson.title}</strong>
          </p>
        )}
        <button type="button" className="btn btn--primary" onClick={onContinue}>
          Continue
        </button>
      </Modal>
    </>
  );
}
