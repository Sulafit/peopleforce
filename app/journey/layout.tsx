import { Suspense } from "react";
import { PlatformShell } from "@/components/platform/PlatformShell";

export default function PlatformLayout({ children }: LayoutProps<"/journey">) {
  // Everything signed-in is driven by client data and the current URL, so it streams in behind this
  // boundary while the static shell is served immediately.
  return (
    <Suspense
      fallback={
        <div className="wrap">
          <div className="screen-note" role="status">
            <p>Loading your journey…</p>
          </div>
        </div>
      }
    >
      <PlatformShell>{children}</PlatformShell>
    </Suspense>
  );
}
