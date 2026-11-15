import type { Metadata } from "next";
import { JourneyScreen } from "@/components/journey/JourneyScreen";

// Signed-in screens render from client data behind the shell, so there is nothing to validate for
// instant navigation here (see node_modules/next/dist/docs: instant-navigation, "Opting out").
export const instant = false;

export const metadata: Metadata = {
  title: "Your journey",
};

export default function JourneyPage() {
  return <JourneyScreen />;
}
