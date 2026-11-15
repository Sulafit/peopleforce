"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { LogoIcon } from "@/components/icons";
import { api } from "@/lib/api/client";
import { useMe } from "@/lib/api/hooks";
import type { MagicLinkState } from "@/lib/api/types";

/**
 * Landing page for the emailed link. Loading it changes nothing on the server: the token is only
 * consumed when the person presses the button (a POST), so mail scanners that prefetch links cannot
 * use it up. The token is removed from the address bar as soon as it has been read.
 */
export function VerifyScreen() {
  const router = useRouter();
  const client = useQueryClient();
  const params = useSearchParams();
  // Captured once; the URL is cleaned right after, so later renders no longer see it.
  const [token] = useState(() => params.get("token"));
  const me = useMe();

  useEffect(() => {
    if (window.location.search) window.history.replaceState(null, "", "/auth/verify");
  }, []);

  const state = useQuery({
    queryKey: ["magic-link", token],
    queryFn: () => api.post<MagicLinkState>("/auth/magic-link/inspect", { token }),
    enabled: !!token,
    retry: false,
    staleTime: Infinity,
    gcTime: 0,
  });

  const verify = useMutation({
    mutationFn: () => api.post<{ redirect: string; is_new_user: boolean }>("/auth/magic-link/verify", { token }),
    onSuccess: (result) => {
      try {
        window.sessionStorage.removeItem("pf.magic-link");
      } catch {
        // nothing to clear
      }
      client.clear();
      router.replace(result.redirect);
    },
  });

  const signedIn = !!me.data;
  const status = verify.isError ? "failed" : !token ? "missing" : (state.data?.status ?? (state.isError ? "failed" : "checking"));
  // A used or missing link is fine when this browser is already signed in.
  const alreadyIn = signedIn && (status === "used" || status === "missing");
  useEffect(() => {
    if (alreadyIn) router.replace("/journey");
  }, [alreadyIn, router]);

  let title = "Checking your link…";
  let text: string | null = null;
  if (status === "valid") {
    title = "Open your journey";
    text = `Confirm to sign in${state.data?.email_masked ? ` as ${state.data.email_masked}` : ""}.`;
  } else if (status === "expired") {
    title = "This link has expired";
    text = "Sign-in links work for a short time. Request a new one and it will arrive in a moment.";
  } else if (status === "used") {
    title = "This link was already used";
    text = "Each link works once. Request a new one to sign in.";
  } else if (status === "invalid" || status === "missing") {
    title = "This link is not valid";
    text = "Open the newest link from your email, or request a new one.";
  } else if (status === "failed") {
    title = "We could not sign you in";
    text = verify.error?.message ?? state.error?.message ?? "Please try again.";
  }

  return (
    <div className="wrap t-yellow">
      <header className="topbar">
        <Link className="brand" href="/">
          <LogoIcon />
          PeopleForce
        </Link>
      </header>
      <main className="auth">
        <div className="card" role={status === "checking" ? "status" : undefined}>
          <h1 className="card__title">{title}</h1>
          {text && <p className="card__intro">{text}</p>}
          <div className="actions">
            {status === "valid" && (
              <button type="button" className="btn btn--primary" disabled={verify.isPending || verify.isSuccess} onClick={() => verify.mutate()}>
                {verify.isPending || verify.isSuccess ? "Signing you in…" : "Continue to my journey"}
              </button>
            )}
            {status !== "valid" && status !== "checking" && !alreadyIn && (
              <Link className="btn btn--primary" href="/login">
                Request a new link
              </Link>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
