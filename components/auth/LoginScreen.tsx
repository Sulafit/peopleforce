"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EmailLinkForm } from "@/components/auth/EmailLinkForm";
import { LogoIcon } from "@/components/icons";
import { useMe } from "@/lib/api/hooks";

export function LoginScreen() {
  const router = useRouter();
  const me = useMe();
  const signedIn = !!me.data;
  useEffect(() => {
    if (signedIn) router.replace("/journey");
  }, [signedIn, router]);

  return (
    <div className="wrap t-yellow">
      <header className="topbar">
        <Link className="brand" href="/">
          <LogoIcon />
          PeopleForce
        </Link>
        <Link className="link-btn" href="/start">
          New here? Start your journey
        </Link>
      </header>
      <main className="auth">
        <div className="auth__intro">
          <h1>Welcome back</h1>
          <p className="hero__lead">Enter your email and we will send a link that opens your journey where you left it.</p>
        </div>
        <EmailLinkForm submitLabel="Email me a sign-in link" source="login" />
      </main>
    </div>
  );
}
