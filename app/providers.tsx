"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { initAnalytics } from "@/lib/analytics";

let browserQueryClient: QueryClient | undefined;

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { staleTime: 15_000 } } });
}

function getQueryClient() {
  // Keep server renders isolated; reuse one client in the browser.
  if (typeof window === "undefined") return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    initAnalytics();
  }, []);
  return <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>;
}
