import type { Metadata } from "next";
import { ProfileScreen } from "@/components/profile/ProfileScreen";

// Rendered from client data behind the platform shell (see app/journey/page.tsx).
export const instant = false;

export const metadata: Metadata = {
  title: "Your profile",
};

export default function ProfilePage() {
  return <ProfileScreen />;
}
