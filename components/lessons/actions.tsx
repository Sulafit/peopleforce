"use client";

import { createContext, use, useState } from "react";
import { CheckIcon } from "@/components/icons";
import { isApiError } from "@/lib/api/client";
import type { LessonAction } from "@/lib/api/types";
import { textFieldSchema } from "@/lib/validation";

type ActionOf<T extends LessonAction["type"]> = Extract<LessonAction, { type: T }>;
/** The slice of a React Query mutation the action components need. Lessons and the daily challenge both fit. */
export interface Submit {
  mutate: (input: { actionKey: string; payload: Record<string, unknown> }) => void;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  variables: { actionKey: string; payload: Record<string, unknown> } | undefined;
}

interface ActionProps<T extends LessonAction["type"]> {
  action: ActionOf<T>;
  submit: Submit;
  /** Titles of the earlier steps this one is waiting for; empty when it can run. */
  waitingFor: string[];
  aiAvailable: boolean;
  /** Hide the action's own title row (when the surrounding dialog already shows it). */
  bare?: boolean;
}

function isPending(submit: Submit, key: string) {
  return submit.isPending && submit.variables?.actionKey === key;
}

function errorFor(submit: Submit, key: string) {
  return submit.isError && submit.variables?.actionKey === key ? submit.error : null;
}

const BareContext = createContext(false);

function ActionFrame({ action, children }: { action: LessonAction; children: React.ReactNode }) {
  const bare = use(BareContext);
  if (bare) return <div className={`action${action.state.completed ? " is-done" : ""}`}>{children}</div>;
  return (
    <div className={`action${action.state.completed ? " is-done" : ""}`}>
      <div className="action__head">
        <span className="check__mark" role="img" aria-label={action.state.completed ? "Done" : "Not done yet"}>
          {action.state.completed && <CheckIcon />}
        </span>
        <h3 className="action__title">{action.title}</h3>
        {!action.required && <span className="chip">Optional</span>}
      </div>
      {action.instructions && <p className="action__text">{action.instructions}</p>}
      {children}
    </div>
  );
}

function Waiting({ titles }: { titles: string[] }) {
  if (titles.length === 0) return null;
  return <p className="hint">First: {titles.join(", ")}.</p>;
}

/**
 * One question per screen. Once the draft is saved it collapses to a short summary with an edit button,
 * so a finished exercise never shows as a wall of text areas.
 */
function TextSubmission({ action, submit }: ActionProps<"text_submission">) {
  const fields = action.config.fields;
  const saved = action.state.payload.values ?? {};
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((field) => [field.name, saved[field.name] ?? ""])),
  );
  const [position, setPosition] = useState(0);
  const [editing, setEditing] = useState(!action.state.completed);
  const [clientError, setClientError] = useState<string | null>(null);

  const error = errorFor(submit, action.key);
  const serverErrors = isApiError(error, "invalid_submission") ? ((error.details.fields ?? {}) as Record<string, string>) : {};
  const pending = isPending(submit, action.key);

  // The server accepted the draft: show the summary. (Adjusting state while rendering, per React docs.)
  const [seenAt, setSeenAt] = useState(action.state.updated_at);
  if (action.state.updated_at !== seenAt) {
    setSeenAt(action.state.updated_at);
    if (action.state.completed) setEditing(false);
  }

  if (!editing) {
    return (
      <ActionFrame action={action}>
        <dl className="answers" data-private>
          {fields.map((field) => (
            <div key={field.name}>
              <dt>{field.label}</dt>
              <dd>{saved[field.name]}</dd>
            </div>
          ))}
        </dl>
        <div className="actions">
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => {
              setPosition(0);
              setEditing(true);
            }}
          >
            Edit answers
          </button>
        </div>
      </ActionFrame>
    );
  }

  const field = fields[position];
  const id = `${action.key}-${field.name}`;
  const value = values[field.name] ?? "";
  const last = position === fields.length - 1;
  const fieldError = clientError ?? serverErrors[field.name] ?? null;

  const next = () => {
    const result = textFieldSchema(field.min_length, field.max_length).safeParse(value);
    if (!result.success) {
      setClientError(result.error.issues[0].message);
      return;
    }
    setClientError(null);
    if (last) submit.mutate({ actionKey: action.key, payload: { values } });
    else setPosition(position + 1);
  };

  return (
    <ActionFrame action={action}>
      {fields.length > 1 && (
        <span className="cap muted">
          Question {position + 1} of {fields.length}
        </span>
      )}
      {/* The key restarts the entrance animation and moves focus for each question. */}
      <div key={field.name} className="field-group field-group--step" data-private>
        <label htmlFor={id}>{field.label}</label>
        {field.help && <p className="hint">{field.help}</p>}
        <textarea
          id={id}
          className="field field--compact"
          rows={3}
          autoFocus={position > 0}
          value={value}
          placeholder={field.example ? `e.g. ${field.example}` : (field.placeholder ?? undefined)}
          aria-invalid={fieldError ? true : undefined}
          aria-describedby={`${id}-foot`}
          onChange={(event) => {
            setValues((old) => ({ ...old, [field.name]: event.target.value }));
            setClientError(null);
          }}
        />
        <div className="field-foot" id={`${id}-foot`}>
          {fieldError ? <span className="hint hint--error">{fieldError}</span> : <span />}
          <span className={`count${value.length > field.max_length ? " is-over" : ""}`} aria-live="polite">
            {value.length} / {field.max_length}
          </span>
        </div>
      </div>
      <div className="actions">
        {position > 0 && (
          <button
            type="button"
            className="btn btn--sm"
            disabled={pending}
            onClick={() => {
              setClientError(null);
              setPosition(position - 1);
            }}
          >
            Previous
          </button>
        )}
        <button type="button" className="btn btn--primary btn--sm" disabled={pending} onClick={next}>
          {pending ? "Saving…" : last ? action.config.submit_label : "Next question"}
        </button>
        {error && !isApiError(error, "invalid_submission") && (
          <span className="hint hint--error" role="alert">
            {error.message}
          </span>
        )}
        {last && !clientError && Object.keys(serverErrors).some((name) => name !== field.name) && (
          <span className="hint hint--error" role="alert">
            An earlier answer needs another look.
          </span>
        )}
      </div>
    </ActionFrame>
  );
}

function Quiz({ action, submit }: ActionProps<"quiz">) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => action.state.payload.answers ?? {});
  const result = action.state.result;
  const review = Object.fromEntries((result.review ?? []).map((item) => [item.question_id, item]));
  const pending = isPending(submit, action.key);
  const error = errorFor(submit, action.key);
  const complete = action.config.questions.every((question) => answers[question.id]);
  const submitted = action.state.payload.answers ?? {};
  const unchanged = action.config.questions.every((question) => answers[question.id] === submitted[question.id]);

  return (
    <ActionFrame action={action}>
      {action.config.questions.map((question, index) => {
        const item = unchanged ? review[question.id] : undefined;
        return (
          <fieldset key={question.id} className="quiz-question">
            <legend>
              {index + 1}. {question.prompt}
            </legend>
            {question.options.map((option) => {
              const checked = answers[question.id] === option.id;
              const mark = item && checked ? (item.correct ? " is-correct" : " is-wrong") : "";
              return (
                <label key={option.id} className={`choice choice--sm${checked ? " is-selected" : ""}${mark}`}>
                  <input
                    type="radio"
                    name={`${action.key}-${question.id}`}
                    checked={checked}
                    onChange={() => setAnswers((old) => ({ ...old, [question.id]: option.id }))}
                  />
                  <span>{option.label}</span>
                </label>
              );
            })}
            {item?.explanation && (
              <p className={`hint${item.correct ? "" : " hint--error"}`}>
                {item.correct ? "Correct. " : "Not quite. "}
                {item.explanation}
              </p>
            )}
          </fieldset>
        );
      })}
      <div className="actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!complete || pending || (unchanged && result.passed === true)}
          onClick={() => submit.mutate({ actionKey: action.key, payload: { answers } })}
        >
          {pending ? "Checking…" : result.passed && unchanged ? "Passed" : "Check answers"}
        </button>
        {result.total !== undefined && unchanged && (
          <span className={result.passed ? "status-line" : "hint hint--error"}>
            {result.correct} of {result.total} correct{result.passed ? "" : ". Adjust your answers and try again."}
          </span>
        )}
        {error && (
          <span className="hint hint--error" role="alert">
            {error.message}
          </span>
        )}
      </div>
    </ActionFrame>
  );
}

function AiReview({ action, submit, waitingFor, aiAvailable }: ActionProps<"ai_review">) {
  const feedback = action.state.result.feedback;
  const pending = isPending(submit, action.key);
  const error = errorFor(submit, action.key);
  const usable = aiAvailable && action.config.supported;

  return (
    <ActionFrame action={action}>
      {!usable && <p className="hint">Coach feedback is not available right now. You can finish the lesson without it.</p>}
      {feedback && (
        <div className="feedback" data-private>
          {action.state.stale && <p className="hint">This feedback is for an earlier draft. Ask again to refresh it.</p>}
          <p className="feedback__summary">{feedback.summary}</p>
          <div className="pills">
            <span className="pill pill--sm">Clarity {feedback.clarity_score}/5</span>
            <span className="pill pill--sm">Specificity {feedback.specificity_score}/5</span>
          </div>
          {feedback.strengths.length > 0 && (
            <div>
              <h4 className="cap section-label">Working well</h4>
              <ul className="feedback__list">
                {feedback.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {feedback.improvements.length > 0 && (
            <div>
              <h4 className="cap section-label">To improve</h4>
              <ul className="feedback__list">
                {feedback.improvements.map((item) => (
                  <li key={item.issue}>
                    <strong>{item.issue}</strong> {item.suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="outcome">
            <span className="cap">A suggestion you can edit</span>
            <p>{feedback.suggested_one_liner}</p>
          </div>
          <p className="hint">AI suggestions are a starting point. Keep only what is true for you.</p>
        </div>
      )}
      <div className="actions">
        <button
          type="button"
          className="btn"
          disabled={!usable || pending || waitingFor.length > 0}
          onClick={() => submit.mutate({ actionKey: action.key, payload: {} })}
        >
          {pending ? "Reading your draft…" : feedback ? "Ask again" : action.config.submit_label}
        </button>
        {error && (
          <span className="hint hint--error" role="alert">
            {error.message}
          </span>
        )}
      </div>
      <Waiting titles={waitingFor} />
    </ActionFrame>
  );
}

function SaveAsset({ action, submit, waitingFor }: ActionProps<"save_asset">) {
  const pending = isPending(submit, action.key);
  const error = errorFor(submit, action.key);
  const saved = action.state.completed && !action.state.stale;

  return (
    <ActionFrame action={action}>
      <div className="actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={pending || waitingFor.length > 0 || saved}
          onClick={() => submit.mutate({ actionKey: action.key, payload: {} })}
        >
          {pending ? "Saving…" : saved ? "Saved to your profile" : action.state.completed ? "Save changes to my profile" : action.config.submit_label}
        </button>
        {action.state.completed && action.state.stale && <span className="hint">Your draft changed since the last save.</span>}
        {error && (
          <span className="hint hint--error" role="alert">
            {error.message}
          </span>
        )}
      </div>
      <Waiting titles={waitingFor} />
    </ActionFrame>
  );
}

function Acknowledge({ action, submit, waitingFor }: ActionProps<"acknowledge">) {
  const pending = isPending(submit, action.key);
  const error = errorFor(submit, action.key);
  return (
    <ActionFrame action={action}>
      <div className="actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={pending || action.state.completed || waitingFor.length > 0}
          onClick={() => submit.mutate({ actionKey: action.key, payload: {} })}
        >
          {action.state.completed ? "Done" : action.config.confirm_label}
        </button>
        {error && (
          <span className="hint hint--error" role="alert">
            {error.message}
          </span>
        )}
      </div>
      <Waiting titles={waitingFor} />
    </ActionFrame>
  );
}

/**
 * A real-world task done a set number of times. The learner ticks off each one; every tick is saved,
 * so they can close the app, do the work, and come back. It is self-reported and says so.
 */
function ExternalTask({ action, submit }: ActionProps<"external_task">) {
  const { target_count: target, unit, tips } = action.config;
  const saved = action.state.payload.count ?? 0;
  const pending = isPending(submit, action.key);
  // Show the tick immediately; the saved count catches up when the request returns.
  const count = pending ? Number(submit.variables?.payload.count ?? saved) : saved;
  const error = errorFor(submit, action.key);

  return (
    <ActionFrame action={action}>
      <div className="tally" role="group" aria-label={`${count} of ${target} done`}>
        {Array.from({ length: target }, (_, index) => {
          const done = index < count;
          return (
            <button
              key={index}
              type="button"
              className={`tally__box${done ? " is-done" : ""}`}
              aria-pressed={done}
              aria-label={`${unit} ${index + 1} of ${target}`}
              disabled={pending || action.state.completed}
              // Tapping the last ticked box undoes it; tapping any other box sets the count up to it.
              onClick={() => submit.mutate({ actionKey: action.key, payload: { count: done && index === count - 1 ? index : index + 1 } })}
            >
              {done ? <CheckIcon size={18} /> : index + 1}
            </button>
          );
        })}
      </div>
      <p className="tally__label" aria-live="polite">
        <strong>
          {count} of {target}
        </strong>{" "}
        · tap a box each time: {unit}
      </p>
      {tips.length > 0 && !action.state.completed && (
        <ul className="feedback__list">
          {tips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      )}
      {error && (
        <p className="hint hint--error" role="alert">
          {error.message}
        </p>
      )}
      {!action.state.completed && <p className="hint">You keep your own count. Progress is saved, so you can come back later today.</p>}
    </ActionFrame>
  );
}

/** Renders one action by type. Unknown types render nothing: the backend only sends supported ones. */
export function ActionView(props: { action: LessonAction; submit: Submit; waitingFor: string[]; aiAvailable: boolean; bare?: boolean }) {
  return (
    <BareContext value={props.bare ?? false}>
      <ActionBody {...props} />
    </BareContext>
  );
}

function ActionBody(props: { action: LessonAction; submit: Submit; waitingFor: string[]; aiAvailable: boolean }) {
  const { action, ...rest } = props;
  switch (action.type) {
    case "external_task":
      return <ExternalTask action={action} {...rest} />;
    case "text_submission":
      return <TextSubmission action={action} {...rest} />;
    case "quiz":
      return <Quiz action={action} {...rest} />;
    case "ai_review":
      return <AiReview action={action} {...rest} />;
    case "save_asset":
      return <SaveAsset action={action} {...rest} />;
    case "acknowledge":
      return <Acknowledge action={action} {...rest} />;
    default:
      return null;
  }
}
