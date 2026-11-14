import type { Metadata } from "next";
// Self-hosted variable fonts: no request to a font CDN at build time or in the browser.
import "@fontsource-variable/fredoka";
import "@fontsource-variable/nunito";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Freelance Growth OS",
    template: "%s — Freelance Growth OS",
  },
  description: "A step-by-step roadmap for building a client-ready freelance presence.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
