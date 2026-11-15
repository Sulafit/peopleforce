import type { Metadata } from "next";
import { Suspense } from "react";
import { LessonScreen } from "@/components/lessons/LessonScreen";

// Signed-in screens render from client data behind the shell, so there is nothing to validate for
// instant navigation here (see node_modules/next/dist/docs: instant-navigation, "Opting out").
export const instant = false;

export const metadata: Metadata = {
  title: "Lesson",
};

export default function LessonPage() {
  // The lesson id is read on the client (useParams), so the page shell stays static.
  return (
    <Suspense
      fallback={
        <div className="wrap">
          <div className="screen-note" role="status">
            <p>Opening your lesson…</p>
          </div>
        </div>
      }
    >
      <LessonScreen />
    </Suspense>
  );
}
