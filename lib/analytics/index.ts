/**
 * Product analytics. One small surface so vendor calls are not scattered around the app.
 * PostHog loads only in the browser and only when NEXT_PUBLIC_POSTHOG_KEY is set.
 *
 * Privacy rules: event properties are ids, enums and counts. Never pass free text the learner wrote,
 * emails, magic links or tokens.
 */

export type AnalyticsEvent =
  | "landing_cta_clicked"
  | "onboarding_started"
  | "onboarding_question_answered"
  | "onboarding_completed"
  | "journey_preview_viewed"
  | "email_link_requested"
  | "journey_viewed"
  | "tour_step_viewed"
  | "lesson_viewed"
  | "platform_content_exported";

type Properties = Record<string, string | number | boolean | null | string[]>;
type PostHog = typeof import("posthog-js").default;

const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.i.posthog.com";

let client: Promise<PostHog | null> | null = null;

function load(): Promise<PostHog | null> {
  if (typeof window === "undefined" || !KEY) return Promise.resolve(null);
  client ??= import("posthog-js")
    .then(({ default: posthog }) => {
      posthog.init(KEY, {
        api_host: HOST,
        person_profiles: "identified_only",
        capture_pageview: "history_change",
        autocapture: false, // only the named events below; no accidental capture of typed text
        // The verify page URL carries the sign-in token until it is stripped.
        before_send: (event) => (event?.properties?.$current_url?.includes("/auth/verify") ? null : event),
        session_recording: {
          maskAllInputs: true,
          maskTextSelector: "[data-private]",
        },
      });
      return posthog;
    })
    .catch(() => null);
  return client;
}

export function initAnalytics(): void {
  void load();
}

export function track(event: AnalyticsEvent, properties?: Properties): void {
  void load().then((posthog) => posthog?.capture(event, properties));
}

/** Link the anonymous visitor to the account. Called once the API confirms who is signed in. */
export function identify(userId: string): void {
  void load().then((posthog) => {
    if (posthog && posthog.get_distinct_id() !== userId) posthog.identify(userId);
  });
}

export function resetAnalytics(): void {
  void load().then((posthog) => posthog?.reset());
}
