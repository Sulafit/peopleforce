"use client";

import { driver, type Driver } from "driver.js";
import "driver.js/dist/driver.css";
import { useEffect, useRef } from "react";

interface HighlightOptions {
  /** Show the highlight. When false nothing is rendered and any open highlight is removed. */
  active: boolean;
  /** `data-tour` name of the element to highlight. */
  anchor: string;
  title: string;
  message: string;
  actionLabel: string;
  onAction: () => void;
  /** The learner closed the popover (X, Escape or a click outside). */
  onDismiss: () => void;
}

const WAIT_MS = 4000;

/** Highlights one anchored element with Driver.js. The element may mount late; we wait briefly for it. */
export function useTourHighlight({ active, anchor, title, message, actionLabel, onAction, onDismiss }: HighlightOptions) {
  const handlers = useRef({ onAction, onDismiss });
  useEffect(() => {
    handlers.current = { onAction, onDismiss };
  });

  useEffect(() => {
    if (!active) return;
    let instance: Driver | null = null;
    let cancelled = false;
    let acted = false;
    let frame = 0;
    const started = performance.now();

    const show = (element: Element) => {
      instance = driver({
        allowClose: true,
        overlayOpacity: 0.55,
        stagePadding: 10,
        stageRadius: 20,
        popoverClass: "pf-tour",
        onDestroyed: () => {
          // Fires for every teardown; only a learner-initiated close counts as a dismissal.
          if (!acted && !cancelled) handlers.current.onDismiss();
        },
      });
      instance.highlight({
        element,
        popover: {
          title,
          description: message,
          showButtons: ["next", "close"],
          nextBtnText: actionLabel,
          onNextClick: () => {
            acted = true;
            instance?.destroy();
            handlers.current.onAction();
          },
        },
      });
    };

    const find = () => {
      if (cancelled) return;
      const element = document.querySelector(`[data-tour="${anchor}"]`);
      if (element) {
        element.scrollIntoView({ block: "center", behavior: "auto" });
        show(element);
      } else if (performance.now() - started < WAIT_MS) {
        frame = requestAnimationFrame(find);
      }
    };
    frame = requestAnimationFrame(find);

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      instance?.destroy();
    };
  }, [active, anchor, title, message, actionLabel]);
}
