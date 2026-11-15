"use client";

import { useEffect, useState } from "react";

/** Animates a number from `from` to `to`. Jumps straight to the end when motion is reduced. */
export function useCountUp(from: number, to: number, durationMs = 900, delayMs = 350): number {
  const [value, setValue] = useState(from);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || from === to) {
      const id = requestAnimationFrame(() => setValue(to));
      return () => cancelAnimationFrame(id);
    }
    let frame = 0;
    const start = performance.now() + delayMs;
    const tick = (now: number) => {
      const t = Math.min(Math.max((now - start) / durationMs, 0), 1);
      setValue(Math.round(from + (to - from) * (1 - (1 - t) ** 3))); // ease-out
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [from, to, durationMs, delayMs]);

  return value;
}
