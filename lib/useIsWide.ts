"use client";

import { useSyncExternalStore } from "react";

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
