import Link from "next/link";
import { LogoIcon, StarIcon } from "@/components/icons";

interface TopBarProps {
  doneCount: number;
  total: number;
  xp: number;
}

export function TopBar({ doneCount, total, xp }: TopBarProps) {
  return (
    <header className="topbar">
      <Link className="brand" href="/">
        <LogoIcon />
        Freelance Growth OS
      </Link>
      <div className="pills">
        <span className="pill">
          {doneCount} of {total} steps
        </span>
        <span className="pill pill--xp">
          <StarIcon />
          {xp} XP
        </span>
      </div>
    </header>
  );
}
