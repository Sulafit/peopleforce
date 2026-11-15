import type { Metadata } from "next";
import { Suspense } from "react";
import { VerifyScreen } from "@/components/auth/VerifyScreen";

export const metadata: Metadata = {
  title: "Sign in",
  // The URL briefly carries the sign-in token: never send it on as a referrer, never index it.
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyScreen />
    </Suspense>
  );
}
