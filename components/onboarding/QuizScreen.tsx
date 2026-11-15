"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowIcon, CheckIcon, LogoIcon } from "@/components/icons";
import { track } from "@/lib/analytics";
import { useCompleteQuiz, useMe, useOnboardingQuiz, useSaveAnswer } from "@/lib/api/hooks";
import type { QuizAnswer, QuizQuestion } from "@/lib/api/types";

function isAnswered(answer: QuizAnswer | undefined): boolean {
  return Array.isArray(answer) ? answer.length > 0 : !!answer;
}

/** The personalization quiz: one question per screen, answers saved server-side as you go. */
export function QuizScreen() {
  const router = useRouter();
  const editing = useSearchParams().get("edit") === "1";
  const quiz = useOnboardingQuiz();
  const me = useMe();
  const save = useSaveAnswer();
  const finish = useCompleteQuiz();
  const [position, setPosition] = useState<number | null>(null);
  // Multi-select choices are held locally until "Continue".
  const [multi, setMulti] = useState<string[] | null>(null);

  const questions = quiz.data?.questions ?? [];
  const answers = quiz.data?.draft?.answers ?? {};
  const firstOpen = questions.findIndex((question) => !isAnswered(answers[question.id]));
  const index = position ?? (firstOpen === -1 ? Math.max(questions.length - 1, 0) : firstOpen);
  const question: QuizQuestion | undefined = questions[index];

  // Returning learners with a finished profile never repeat the quiz.
  const hasProfile = me.data ? !me.data.onboarding_required : false;
  const alreadyDone = quiz.data?.draft?.status === "completed" && !editing && position === null;
  useEffect(() => {
    if (hasProfile) router.replace("/journey");
    else if (alreadyDone) router.replace("/start/plan");
  }, [hasProfile, alreadyDone, router]);

  if (quiz.isError) {
    return (
      <QuizFrame progress={0}>
        <div className="screen-note" role="alert">
          <p>{quiz.error.message}</p>
          <button type="button" className="btn" onClick={() => quiz.refetch()}>
            Try again
          </button>
        </div>
      </QuizFrame>
    );
  }
  if (!question || hasProfile || alreadyDone) {
    return (
      <QuizFrame progress={0}>
        <div className="screen-note" role="status">
          <p>Loading…</p>
        </div>
      </QuizFrame>
    );
  }

  const last = index === questions.length - 1;
  const saved = answers[question.id];
  const selectedMulti = multi ?? (Array.isArray(saved) ? saved : []);
  const busy = save.isPending || finish.isPending;
  const error = save.error ?? finish.error;

  const advance = () => {
    setMulti(null);
    if (!last) {
      setPosition(index + 1);
      return;
    }
    finish.mutate(undefined, {
      onSuccess: () => {
        track("onboarding_completed");
        router.push("/start/plan");
      },
    });
  };

  const answer = (value: QuizAnswer) => {
    if (!quiz.data?.draft) track("onboarding_started");
    save.mutate(
      { question_id: question.id, value },
      {
        onSuccess: () => {
          track("onboarding_question_answered", { question_id: question.id, step: index + 1 });
          advance();
        },
      },
    );
  };

  const toggle = (value: string, exclusive: boolean) => {
    const exclusiveValues = question.options.filter((option) => option.exclusive).map((option) => option.value);
    setMulti(() => {
      if (selectedMulti.includes(value)) return selectedMulti.filter((item) => item !== value);
      if (exclusive) return [value];
      return [...selectedMulti.filter((item) => !exclusiveValues.includes(item)), value];
    });
  };

  return (
    <QuizFrame progress={(index + (isAnswered(saved) ? 1 : 0)) / questions.length}>
      <div className="quiz__meta">
        <span className="cap muted">
          Question {index + 1} of {questions.length}
        </span>
      </div>
      {/* The key restarts the entrance animation for each question. */}
      <div key={question.id} className="quiz__question">
        <h1 id="quiz-title">{question.title}</h1>
        {question.helper && <p className="hero__lead">{question.helper}</p>}

        <div
          className="choices"
          role={question.kind === "single" ? "radiogroup" : "group"}
          aria-labelledby="quiz-title"
        >
          {question.options.map((option) => {
            const selected = question.kind === "single" ? saved === option.value : selectedMulti.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                role={question.kind === "single" ? "radio" : "checkbox"}
                aria-checked={selected}
                className={`choice${selected ? " is-selected" : ""}`}
                disabled={option.disabled || busy}
                onClick={() => (question.kind === "single" ? answer(option.value) : toggle(option.value, option.exclusive))}
              >
                <span className="choice__mark" aria-hidden="true">
                  {selected && <CheckIcon />}
                </span>
                <span className="choice__label">{option.label}</span>
                {option.note && <span className="chip">{option.note}</span>}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <p className="hint hint--error" role="alert">
          {error.message}
        </p>
      )}

      <div className="actions actions--split quiz__nav">
        <button type="button" className="btn" disabled={index === 0 || busy} onClick={() => (setMulti(null), setPosition(index - 1))}>
          <ArrowIcon back />
          Back
        </button>
        {question.kind === "multi" ? (
          <button type="button" className="btn btn--primary" disabled={selectedMulti.length === 0 || busy} onClick={() => answer(selectedMulti)}>
            {last ? "See my journey" : "Continue"}
            <ArrowIcon />
          </button>
        ) : (
          isAnswered(saved) && (
            <button type="button" className="btn btn--primary" disabled={busy} onClick={advance}>
              {finish.isPending ? "Building your journey…" : last ? "See my journey" : "Continue"}
              <ArrowIcon />
            </button>
          )
        )}
      </div>
    </QuizFrame>
  );
}

function QuizFrame({ progress, children }: { progress: number; children: React.ReactNode }) {
  return (
    <div className="wrap t-yellow">
      <header className="topbar">
        <Link className="brand" href="/">
          <LogoIcon />
          PeopleForce
        </Link>
        <Link className="link-btn" href="/login">
          I already have an account
        </Link>
      </header>
      <main className="quiz">
        <div
          className="progress"
          role="progressbar"
          aria-label="Quiz progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
        >
          <div className="progress__fill" style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
        {children}
      </main>
    </div>
  );
}
