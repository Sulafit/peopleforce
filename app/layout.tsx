import type { Metadata } from "next";
// Self-hosted variable fonts: no request to a font CDN at build time or in the browser.
import "@fontsource-variable/fredoka";
import "@fontsource-variable/nunito";
import "./tailwind.css";
import "./globals.css";
import { Providers } from "./providers";

// Canonical origin for absolute URLs in metadata (Open Graph, canonical links).
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://peopleforce.site";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "PeopleForce",
    template: "%s — PeopleForce",
  },
  description: "A step-by-step path for skilled professionals to start and grow a freelance business.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
