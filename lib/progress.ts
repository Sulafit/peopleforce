"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";
import { DEMO_DONE } from "@/lib/roadmap";

/*
  Finished step ids, kept in localStorage so a refresh keeps the progress.
  This is the one place to swap for a real API once there is a backend.
*/

const KEY = "fgos.progress.v1";
const listeners = new Set<() => void>();
let memory: string | null = null; // used when storage is unavailable

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function read(): string | null {
  try {
    return window.localStorage.getItem(KEY) ?? memory;
  } catch {
    return memory;
  }
}

function write(ids: string[]) {
  memory = JSON.stringify(ids);
  try {
    window.localStorage.setItem(KEY, memory);
  } catch {
    // progress then lives only in memory
  }
  listeners.forEach((listener) => listener());
}

function parse(raw: string | null): string[] {
  if (!raw) return DEMO_DONE;
  try {
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value) ? value.filter((id): id is string => typeof id === "string") : DEMO_DONE;
  } catch {
    return DEMO_DONE;
  }
}

export function useProgress() {
  const raw = useSyncExternalStore(subscribe, read, () => null);
  const done = useMemo(() => new Set(parse(raw)), [raw]);

  const markDone = useCallback((stepId: string) => {
    const ids = parse(read());
    if (!ids.includes(stepId)) write([...ids, stepId]);
  }, []);

  const reset = useCallback(() => write(DEMO_DONE), []);

  return { done, markDone, reset };
}

/** True from the width where the step drawer sits beside the map instead of over it. */
export function useIsWide(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia("(min-width: 1041px)");
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () => window.matchMedia("(min-width: 1041px)").matches,
    () => false,
  );
}
