"use client";

import Link from "next/link";
import { ArrowIcon } from "@/components/icons";
import { track } from "@/lib/analytics";

interface StartCtaProps {
  /** Where on the page this button sits; sent with the analytics event. */
  location: "header" | "hero" | "how" | "path" | "final";
  label?: string;
  size?: "sm" | "md" | "lg";
}

/** Every landing CTA leads to the same place: the quiz, which starts or resumes onboarding. */
export function StartCta({ location, label = "Start your freelance journey", size = "md" }: StartCtaProps) {
  const sizeClass = size === "sm" ? " btn--sm" : size === "lg" ? " btn--lg" : "";
  return (
    <Link className={`btn btn--primary${sizeClass}`} href="/start" onClick={() => track("landing_cta_clicked", { location })}>
      {label}
      {size !== "sm" && <ArrowIcon />}
    </Link>
  );
}
