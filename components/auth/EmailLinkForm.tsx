"use client";

import { useEffect, useState } from "react";
import { track } from "@/lib/analytics";
import { isApiError } from "@/lib/api/client";
import { useRequestMagicLink } from "@/lib/api/hooks";
import type { MagicLinkSent } from "@/lib/api/types";
import { emailSchema } from "@/lib/validation";

const STORAGE_KEY = "pf.magic-link";

interface Stored {
  email: string;
  sent: MagicLinkSent;
  at: number;
}

function readStored(): Stored | null {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    const value = raw ? (JSON.parse(raw) as Stored) : null;
    // Forget it once the link itself has expired.
    return value && Date.now() - value.at < value.sent.expires_in_minutes * 60_000 ? value : null;
  } catch {
    return null;
  }
}

function writeStored(value: Stored | null) {
  try {
    if (value) window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    else window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // The "sent" screen then simply does not survive a refresh.
  }
}

function waitText(seconds: number): string {
  return seconds < 60 ? `${Math.ceil(seconds)} seconds` : `${Math.ceil(seconds / 60)} min`;
}

/**
 * Email field -> "check your inbox". No passwords and no codes: the emailed link is the credential.
 * The address is kept in sessionStorage for this tab only, so a refresh keeps the "sent" state.
 */
export function EmailLinkForm({ submitLabel, source }: { submitLabel: string; source: "onboarding" | "login" }) {
  const request = useRequestMagicLink();
  const [email, setEmail] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);
  const [stored, setStored] = useState<Stored | null>(null);
  // 0 until mounted: the clock is only read in the browser, never during prerender.
  const [now, setNow] = useState(0);

  useEffect(() => {
    // Client-only state: read after mount so server and client markup match.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStored(readStored());
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const send = (address: string) => {
    const parsed = emailSchema.safeParse(address);
    if (!parsed.success) {
      setInvalid(parsed.error.issues[0].message);
      return;
    }
    setInvalid(null);
    request.mutate(parsed.data, {
      onSuccess: (sent) => {
        const value = { email: parsed.data, sent, at: Date.now() };
        writeStored(value);
        setStored(value);
        setNow(Date.now());
        track("email_link_requested", { source });
      },
    });
  };

  const error = request.error;
  const errorText = !error
    ? null
    : isApiError(error, "rate_limited")
      ? `Please wait ${waitText(Number(error.details.retry_after_seconds ?? 60))} before asking for another email.`
      : isApiError(error, "validation_error")
        ? "Enter a valid email address."
        : error.message;

  if (stored) {
    const waitLeft = Math.max(0, Math.ceil((stored.at + stored.sent.resend_after_seconds * 1000 - now) / 1000));
    return (
      <div className="card" role="status">
        <h2 className="card__title">Check your inbox</h2>
        <p className="card__intro">
          We sent a sign-in link to <strong data-private>{stored.sent.email_masked}</strong>. Open it on any device to
          continue. It works once and expires in {stored.sent.expires_in_minutes} minutes.
        </p>
        {stored.sent.dev_link && (
          <p className="callout callout--info">
            <span className="cap">Development mode</span>
            No email was sent.{" "}
            <a href={stored.sent.dev_link} data-private>
              Open the sign-in link
            </a>
          </p>
        )}
        {errorText && (
          <p className="hint hint--error" role="alert">
            {errorText}
          </p>
        )}
        <div className="actions">
          <button type="button" className="btn" disabled={waitLeft > 0 || request.isPending} onClick={() => send(stored.email)}>
            {request.isPending ? "Sending…" : waitLeft > 0 ? `Resend in ${waitLeft}s` : "Resend email"}
          </button>
          <button
            type="button"
            className="link-btn"
            onClick={() => {
              writeStored(null);
              setStored(null);
              request.reset();
            }}
          >
            Use a different email
          </button>
        </div>
      </div>
    );
  }

  return (
    <form
      className="card"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        send(email);
      }}
    >
      <div className="field-group">
        <label htmlFor="email">Your email</label>
        <input
          id="email"
          className="field field--input"
          type="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          placeholder="you@example.com"
          value={email}
          aria-invalid={invalid ? true : undefined}
          aria-describedby="email-note"
          onChange={(event) => {
            setEmail(event.target.value);
            setInvalid(null);
          }}
          data-private
        />
        <p id="email-note" className={invalid || errorText ? "hint hint--error" : "hint"} role={invalid || errorText ? "alert" : undefined}>
          {invalid ?? errorText ?? "No password needed. We email you a link that signs you in."}
        </p>
      </div>
      <div className="actions">
        <button type="submit" className="btn btn--primary" disabled={request.isPending}>
          {request.isPending ? "Sending…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
