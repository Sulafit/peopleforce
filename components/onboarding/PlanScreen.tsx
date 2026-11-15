"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { EmailLinkForm } from "@/components/auth/EmailLinkForm";
import { ArrowIcon, ClockIcon, LogoIcon } from "@/components/icons";
import { track } from "@/lib/analytics";
import { isApiError } from "@/lib/api/client";
import { useClaimDraft, useMe, usePreview } from "@/lib/api/hooks";

/** The personalized journey preview shown after the quiz and before any email is asked for. */
export function PlanScreen() {
  const router = useRouter();
  const preview = usePreview();
  const me = useMe();
  const claim = useClaimDraft();
  const [saving, setSaving] = useState(false);
  const formRef = useRef<HTMLDivElement>(null);

  const error = preview.error;
  const missing = isApiError(error, "quiz_incomplete") || isApiError(error, "draft_not_found");
  useEffect(() => {
    if (missing) router.replace("/start");
  }, [missing, router]);

  const ready = !!preview.data;
  useEffect(() => {
    if (ready) track("journey_preview_viewed");
  }, [ready]);

  useEffect(() => {
    if (saving) formRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [saving]);

  if (!preview.data) {
    return (
      <div className="wrap">
        <div className="screen-note" role="status">
          {error && !missing ? (
            <>
              <p>{error.message}</p>
              <button type="button" className="btn" onClick={() => preview.refetch()}>
                Try again
              </button>
            </>
          ) : (
            <p>Building your journey…</p>
          )}
        </div>
      </div>
    );
  }

  const plan = preview.data;
  const signedIn = !!me.data;

  const saveJourney = () => {
    if (signedIn) {
      // Already signed in (for example the quiz was retaken): attach the answers directly.
      claim.mutate(undefined, { onSuccess: (result) => router.replace(result.redirect) });
    } else {
      setSaving(true);
    }
  };

  return (
    <div className="wrap t-yellow">
      <header className="topbar">
        <Link className="brand" href="/">
          <LogoIcon />
          PeopleForce
        </Link>
        <Link className="link-btn" href="/start?edit=1">
          Change my answers
        </Link>
      </header>

      <main className="plan">
        <section className="plan__intro">
          <span className="cap muted">Your personalized journey</span>
          <h1>{plan.headline}</h1>
          <div className="pills">
            <span className="pill pill--sm">{plan.specialization_label}</span>
            <span className="pill pill--sm">{plan.stage_label}</span>
            <span className="pill pill--sm pill--xp">{plan.goal_label}</span>
          </div>
          <p className="hero__lead">{plan.stage_line}</p>
        </section>

        <div className="plan__grid">
          <section className="card">
            <h2 className="card__title">Your first milestones</h2>
            <ol>
              {plan.milestones.map((milestone, index) => (
                <li key={milestone} className="part">
                  <span className="part__n">{index + 1}</span>
                  <span className="part__text">
                    <span className="part__title">{milestone}</span>
                  </span>
                </li>
              ))}
            </ol>
            <div className="outcome">
              <span className="cap">You start with</span>
              <p>
                {plan.first_lesson_title}{" "}
                <span className="muted">
                  · <ClockIcon /> {plan.first_lesson_minutes} min
                </span>
              </p>
            </div>
          </section>

          <section className="plan__path" aria-label="Learning path preview">
            <h2 className="cap muted">
              The road ahead · {plan.chapters.length} levels, {plan.total_lessons} steps
            </h2>
            <ol className="plan__levels">
              {plan.chapters.map((chapter, index) => (
                <li key={chapter.title} className={`sign sign--flat t-${chapter.theme}`}>
                  <span className="sign__badge" aria-hidden="true">
                    {index + 1}
                  </span>
                  <div className="sign__body">
                    <div className="sign__head">
                      <h3 className="sign__title sign__title--sm">{chapter.title}</h3>
                      <span className="chip">{chapter.lesson_count} steps</span>
                    </div>
                    <p className="sign__blurb">{chapter.blurb}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>

        <section className="plan__save" ref={formRef}>
          {saving ? (
            <>
              <h2 className="card__title">Save your journey</h2>
              <p className="hero__lead">Enter your email and we will send a link that opens your journey. Your answers are kept with it.</p>
              <EmailLinkForm submitLabel="Email me my link" source="onboarding" />
            </>
          ) : (
            <>
              <button type="button" className="btn btn--primary btn--lg" disabled={claim.isPending} onClick={saveJourney}>
                {claim.isPending ? "Saving…" : "Save my journey"}
                <ArrowIcon />
              </button>
              <p className="hint">This plan is built from your answers. It is saved to your account in the next step.</p>
              {claim.isError && (
                <p className="hint hint--error" role="alert">
                  {claim.error.message}
                </p>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}
