"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AvatarPicker } from "@/components/avatar/AvatarPicker";
import { Avatar, avatarLabel } from "@/components/avatar/avatars";
import { ArrowIcon, CheckIcon, FlameIcon, LockIcon, StarIcon } from "@/components/icons";
import { TopBar } from "@/components/roadmap/TopBar";
import { resetAnalytics } from "@/lib/analytics";
import { useLogout, useProfilePage } from "@/lib/api/hooks";
import type { Asset } from "@/lib/api/types";

const ASSET_LABEL: Record<string, string> = {
  freelancer_offer: "Freelance offer",
  professional_bio: "Professional bio",
  portfolio_case_study: "Portfolio case study",
  upwork_profile_draft: "Upwork profile draft",
  fiverr_gig_draft: "Fiverr gig draft",
  linkedin_post_draft: "LinkedIn post draft",
};

const WEEKDAY = new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: "UTC" });

function AssetCard({ asset }: { asset: Asset }) {
  const fields = Array.isArray(asset.content.fields)
    ? (asset.content.fields as { name: string; label: string; value: string }[])
    : null;
  return (
    <li className="side-card">
      <div className="sign__head">
        <h3 className="asset__title">{ASSET_LABEL[asset.asset_type] ?? asset.asset_type}</h3>
        <span className="chip">{asset.status === "draft" ? "Draft" : "Saved"}</span>
      </div>
      {fields ? (
        <dl className="answers" data-private>
          {fields.map((field) => (
            <div key={field.name}>
              <dt>{field.label}</dt>
              <dd>{field.value}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <div className="answers" data-private>
          <p className="asset__title">{String(asset.content.title ?? "")}</p>
          <p>{String(asset.content.body ?? "")}</p>
        </div>
      )}
    </li>
  );
}

/** Profile: the learner's character, XP rank ladder, streak, achievements and the assets they built. */
export function ProfileScreen() {
  const router = useRouter();
  const page = useProfilePage();
  const logout = useLogout();
  const [choosing, setChoosing] = useState(false);

  if (!page.data) {
    return (
      <div className="wrap">
        <div className="screen-note" role="status">
          {page.error ? (
            <>
              <p>{page.error.message}</p>
              <button type="button" className="btn" onClick={() => page.refetch()}>
                Try again
              </button>
            </>
          ) : (
            <p>Loading your profile…</p>
          )}
        </div>
      </div>
    );
  }

  const { profile, rank, ranks, streak, achievements, assets, xp_total: xp } = page.data;
  const earned = achievements.filter((achievement) => achievement.earned).length;

  const signOut = () =>
    logout.mutate(undefined, {
      onSuccess: () => {
        resetAnalytics();
        router.replace("/");
      },
    });

  return (
    <div className="wrap t-violet">
      <TopBar xp={xp} rank={rank} streak={streak} avatarKey={profile.avatar_key} />

      <main className="profile">
        <Link className="btn btn--sm profile__back" href="/journey">
          <ArrowIcon back />
          Journey
        </Link>

        <section className="profile__head">
          <button
            type="button"
            className="profile__avatar"
            onClick={() => setChoosing(true)}
            aria-label={profile.avatar_key ? `Your character: ${avatarLabel(profile.avatar_key)}. Change it` : "Choose your character"}
          >
            {profile.avatar_key ? <Avatar avatarKey={profile.avatar_key} size={104} /> : <span className="profile__blank">?</span>}
            <span className="chip profile__edit">Change</span>
          </button>
          <div className="profile__who">
            <span className="cap muted">
              Rank {rank.number} of {ranks.length}
            </span>
            <h1>{rank.title}</h1>
            <p className="hero__lead">
              {profile.specialization_label} · {profile.goal_label}
            </p>
            <p className="hint" data-private>
              {page.data.email}
            </p>
          </div>
        </section>

        <div className="profile__grid">
          <section className="card t-yellow" aria-labelledby="rank-title">
            <h2 id="rank-title" className="card__title">
              Your XP journey
            </h2>
            <div>
              <div className="rank-bar__labels">
                <span>
                  <StarIcon size={14} /> {xp} XP
                </span>
                <span>{rank.next_title ? `${rank.next_min_xp! - xp} XP to ${rank.next_title}` : "Top rank reached"}</span>
              </div>
              <div
                className="progress"
                role="progressbar"
                aria-label="Progress to the next rank"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(rank.progress * 100)}
              >
                <div className="progress__fill" style={{ width: `${Math.round(rank.progress * 100)}%` }} />
              </div>
            </div>
            <ol className="ranks">
              {ranks.map((step) => (
                <li key={step.number} className={`rank${step.reached ? " is-reached" : ""}${step.current ? " is-current" : ""}`}>
                  <span className="part__n">{step.reached ? <CheckIcon /> : step.number}</span>
                  <span className="rank__title">{step.title}</span>
                  {step.current && <span className="here">You are here</span>}
                  <span className="part__min">{step.min_xp} XP</span>
                </li>
              ))}
            </ol>
            <p className="hint">Lessons and the daily challenge earn XP.</p>
          </section>

          <div className="profile__col">
            <section className="card t-orange" aria-labelledby="streak-title">
              <h2 id="streak-title" className="card__title">
                Streak
              </h2>
              <div className="streak__numbers">
                <div>
                  <span className="streak__value">
                    <FlameIcon size={26} lit={streak.current > 0} />
                    {streak.current}
                  </span>
                  <span className="hint">{streak.current === 1 ? "day in a row" : "days in a row"}</span>
                </div>
                <div>
                  <span className="streak__value">{streak.longest}</span>
                  <span className="hint">longest</span>
                </div>
              </div>
              <ol className="week" aria-label="Last seven days">
                {streak.week.map((day) => (
                  <li key={day.day} className={day.active ? "is-active" : ""}>
                    <span className="week__dot" role="img" aria-label={day.active ? "Active" : "No activity"}>
                      {day.active && <CheckIcon size={12} />}
                    </span>
                    <span>{WEEKDAY.format(new Date(`${day.day}T12:00:00Z`))}</span>
                  </li>
                ))}
              </ol>
              <p className="hint">
                {streak.active_today ? "Today is counted. See you tomorrow." : "Finish a lesson step or today's challenge to count today."}
              </p>
            </section>

            <section className="card t-green" aria-labelledby="ach-title">
              <h2 id="ach-title" className="card__title">
                Achievements{" "}
                <span className="muted">
                  {earned}/{achievements.length}
                </span>
              </h2>
              <ul className="badges">
                {achievements.map((achievement) => (
                  <li key={achievement.key} className={`badge${achievement.earned ? " is-earned" : ""}`}>
                    <span className="badge__icon" aria-hidden="true">
                      {achievement.earned ? <StarIcon size={18} fill="#FFC83D" /> : <LockIcon size={14} />}
                    </span>
                    <span>
                      <strong>{achievement.title}</strong>
                      <span className="hint"> {achievement.description}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>

        <section aria-labelledby="assets-title" className="profile__assets">
          <h2 id="assets-title" className="card__title">
            What you have built
          </h2>
          {assets.length === 0 ? (
            <p className="hero__lead">Nothing yet. Your first lesson saves your freelance offer here.</p>
          ) : (
            <ul className="profile__asset-list">
              {assets.map((asset) => (
                <AssetCard key={asset.id} asset={asset} />
              ))}
            </ul>
          )}
        </section>

        <p className="page-foot">
          <button type="button" className="link-btn" onClick={signOut} disabled={logout.isPending}>
            Sign out
          </button>
        </p>
      </main>

      {choosing && (
        <AvatarPicker
          avatars={page.data.avatars}
          current={profile.avatar_key}
          eyebrow="Your character"
          message="Choose a character to accompany you on your journey."
          onClose={() => setChoosing(false)}
          onSelected={() => {
            setChoosing(false);
            void page.refetch();
          }}
        />
      )}
    </div>
  );
}
