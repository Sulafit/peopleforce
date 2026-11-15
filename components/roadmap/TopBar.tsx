import Link from "next/link";
import { Avatar } from "@/components/avatar/avatars";
import { FlameIcon, LogoIcon, StarIcon } from "@/components/icons";
import type { Rank, Streak } from "@/lib/api/types";

interface TopBarProps {
  xp: number;
  rank: Rank;
  streak: Streak;
  avatarKey: string | null;
}

/** Signed-in header: brand, streak, XP with rank, and the avatar that opens the profile page. */
export function TopBar({ xp, rank, streak, avatarKey }: TopBarProps) {
  const streakHint = streak.active_today
    ? `${streak.current}-day streak. Done for today.`
    : streak.current > 0
      ? `${streak.current}-day streak. Do something today to keep it.`
      : "Finish a step or today's challenge to start a streak.";

  return (
    <header className="topbar">
      <Link className="brand" href="/journey">
        <LogoIcon />
        PeopleForce
      </Link>
      <div className="pills">
        <span className={`pill${streak.active_today ? " pill--streak" : ""}`} title={streakHint} data-tour="streak">
          <FlameIcon lit={streak.active_today} />
          <span aria-label={streakHint}>{streak.current}</span>
        </span>
        <span className="pill pill--xp" data-tour="xp-total">
          <StarIcon />
          {xp} XP
        </span>
        <Link className="pill pill--profile" href="/journey/profile" aria-label={`Your profile. Rank ${rank.number}, ${rank.title}`}>
          <span className="pill__avatar">{avatarKey ? <Avatar avatarKey={avatarKey} size={30} /> : <span className="pill__blank" />}</span>
          {rank.title}
        </Link>
      </div>
    </header>
  );
}
