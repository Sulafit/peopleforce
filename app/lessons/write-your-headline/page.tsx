import type { Metadata } from "next";
import { HeadlineLesson } from "@/components/lesson/HeadlineLesson";

export const metadata: Metadata = {
  title: "Write your headline",
};

export default function HeadlineLessonPage() {
  return <HeadlineLesson />;
}
