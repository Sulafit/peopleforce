import type { Metadata } from "next";
import { Suspense } from "react";
import { QuizScreen } from "@/components/onboarding/QuizScreen";

export const metadata: Metadata = {
  title: "Start your freelance journey",
};

export default function StartPage() {
  return (
    <Suspense fallback={null}>
      <QuizScreen />
    </Suspense>
  );
}
