import type { Metadata } from "next";
import { Landing } from "@/components/landing/Landing";

export const metadata: Metadata = {
  title: "PeopleForce — Turn your skills into a freelance business",
};

export default function LandingPage() {
  return <Landing />;
}
