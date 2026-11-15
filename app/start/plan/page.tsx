import type { Metadata } from "next";
import { PlanScreen } from "@/components/onboarding/PlanScreen";

export const metadata: Metadata = {
  title: "Your journey",
};

export default function PlanPage() {
  return <PlanScreen />;
}
