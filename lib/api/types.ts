/** Response shapes of the PeopleForce API. Mirrors the Pydantic schemas in api/src/peopleforce/modules. */

import type { PartKind, Theme } from "@/lib/roadmap";

export interface QuizOption {
  value: string;
  label: string;
  disabled: boolean;
  note: string | null;
  exclusive: boolean;
}

export interface QuizQuestion {
  id: string;
  title: string;
  kind: "single" | "multi";
  helper: string | null;
  options: QuizOption[];
}

export type QuizAnswer = string | string[];

export interface OnboardingDraft {
  status: "in_progress" | "completed";
  answers: Record<string, QuizAnswer>;
}

export interface OnboardingQuiz {
  questions: QuizQuestion[];
  draft: OnboardingDraft | null;
}

export interface JourneyPreview {
  headline: string;
  specialization_label: string;
  stage_label: string;
  stage_line: string;
  goal_label: string;
  channel_label: string;
  milestones: string[];
  chapters: { title: string; theme: Theme; blurb: string; lesson_count: number }[];
  first_lesson_title: string;
  first_lesson_minutes: number;
  total_lessons: number;
}

export interface MagicLinkSent {
  status: "sent";
  email_masked: string;
  expires_in_minutes: number;
  resend_after_seconds: number;
  dev_link: string | null;
}

export interface MagicLinkState {
  status: "valid" | "expired" | "used" | "invalid";
  email_masked: string | null;
}

export interface Profile {
  display_name: string | null;
  avatar_key: string | null;
  timezone: string;
  domain: string;
  specialization: string;
  specialization_label: string;
  role_label: string;
  experience_level: string;
  freelance_stage: string;
  stage_label: string;
  existing_assets: string[];
  acquisition_channel: string;
  channel_label: string;
  primary_goal: string;
  goal_label: string;
}

export interface Me {
  id: string;
  email: string;
  profile: Profile | null;
  onboarding_required: boolean;
}

export type TourStage =
  | "journey_intro"
  | "first_lesson_started"
  | "avatar_selection"
  | "first_reward_claimed"
  | "next_lesson_prompt"
  | "completed";

export interface Tour {
  stage: TourStage;
  status: "active" | "skipped" | "completed";
}

export type TourEvent = "first_lesson_opened" | "reward_acknowledged" | "next_prompt_acknowledged" | "skip" | "replay";

export interface LessonPart {
  kind: PartKind;
  title: string;
  minutes: number;
}

export interface LessonNode {
  id: string;
  title: string;
  minutes: number;
  xp: number;
  summary: string;
  parts: LessonPart[];
  output: string;
  status: "done" | "current" | "locked";
  reward_pending: boolean;
  started: boolean;
  playable: boolean;
}

export interface Chapter {
  id: string;
  theme: Theme;
  tier: string;
  title: string;
  blurb: string;
  lessons: LessonNode[];
}

export interface Achievement {
  key: string;
  title: string;
  description: string;
  earned: boolean;
  earned_at: string | null;
}

export interface LessonRef {
  id: string;
  title: string;
  playable: boolean;
}

export interface Rank {
  number: number;
  title: string;
  min_xp: number;
  next_title: string | null;
  next_min_xp: number | null;
  xp_into: number;
  xp_span: number | null;
  progress: number;
}

export interface RankStep {
  number: number;
  title: string;
  min_xp: number;
  reached: boolean;
  current: boolean;
}

export interface Streak {
  current: number;
  longest: number;
  active_today: boolean;
  week: { day: string; active: boolean }[];
}

export interface Reward {
  lesson_id: string;
  lesson_title: string;
  xp_awarded: number;
  xp_total: number;
  achievements: Achievement[];
  next_lesson: LessonRef | null;
  rank: Rank;
  rank_up: boolean;
}

export interface Journey {
  path_id: string;
  path_title: string;
  track_label: string;
  welcome: string;
  chapters: Chapter[];
  first_lesson_id: string;
  current_lesson_id: string | null;
  pending_reward_lesson_id: string | null;
  last_reward: Reward | null;
  xp_total: number;
  rank: Rank;
  streak: Streak;
  completed_count: number;
  total_count: number;
  profile: Profile;
  tour: Tour;
  achievements: Achievement[];
  avatars: string[];
  more_coming: string | null;
}

export type Block =
  | { type: "markdown"; key: string; title: string | null; body: string }
  | { type: "youtube"; key: string; title: string; video_id: string }
  | { type: "callout"; key: string; tone: "info" | "tip" | "warning"; title: string | null; body: string }
  | { type: "resources"; key: string; title: string | null; links: { label: string; url: string; description: string | null }[] }
  | { type: "action_group" | "quiz" | "ai_feedback"; key: string; title: string | null; intro: string | null; action_keys: string[] };

export interface TextFieldConfig {
  name: string;
  label: string;
  help: string | null;
  placeholder: string | null;
  multiline: boolean;
  min_length: number;
  max_length: number;
  example: string | null;
}

export interface QuizReviewItem {
  question_id: string;
  correct: boolean;
  correct_option_id: string;
  explanation: string | null;
}

export interface WritingFeedback {
  summary: string;
  strengths: string[];
  improvements: { issue: string; suggestion: string }[];
  clarity_score: number;
  specificity_score: number;
  suggested_one_liner: string;
}

export interface ActionState<P = Record<string, unknown>, R = Record<string, unknown>> {
  completed: boolean;
  payload: P;
  result: R;
  updated_at: string | null;
  stale: boolean;
}

interface ActionBase {
  key: string;
  title: string;
  instructions: string | null;
  required: boolean;
  blocked_by: string[];
}

export type LessonAction =
  | (ActionBase & { type: "acknowledge"; config: { confirm_label: string }; state: ActionState })
  | (ActionBase & {
      type: "text_submission";
      config: { submit_label: string; fields: TextFieldConfig[] };
      state: ActionState<{ values?: Record<string, string> }>;
    })
  | (ActionBase & {
      type: "quiz";
      config: { passing_score: number; questions: { id: string; prompt: string; options: { id: string; label: string }[] }[] };
      state: ActionState<
        { answers?: Record<string, string> },
        { score?: number; correct?: number; total?: number; passed?: boolean; review?: QuizReviewItem[] }
      >;
    })
  | (ActionBase & {
      type: "ai_review";
      config: { source_action_key: string; submit_label: string; supported: boolean };
      state: ActionState<Record<string, unknown>, { feedback?: WritingFeedback }>;
    })
  | (ActionBase & {
      type: "external_task";
      config: { target_count: number; unit: string; tips: string[] };
      state: ActionState<{ count?: number }, { count?: number; target?: number }>;
    })
  | (ActionBase & {
      type: "save_asset";
      config: { asset_type: string; source_action_key: string; submit_label: string };
      state: ActionState<Record<string, unknown>, { asset_id?: string; revision?: number }>;
    });

export interface Lesson {
  id: string;
  title: string;
  minutes: number;
  xp: number;
  summary: string;
  output: string;
  parts: LessonPart[];
  chapter: { id: string; title: string; theme: Theme; index: number; lesson_index: number; lesson_count: number };
  is_first_lesson: boolean;
  status: "done" | "current";
  progress_status: "not_started" | "in_progress" | "reward_pending" | "completed";
  blocks: Block[];
  actions: LessonAction[];
  completable: boolean;
  missing_required: string[];
  ai_available: boolean;
  content_version: string;
  next_lesson: LessonRef | null;
  tour: Tour;
}

export interface ActionSubmitResult {
  action: LessonAction;
  actions: LessonAction[];
  completable: boolean;
  missing_required: string[];
  achievements: Achievement[];
}

export interface CompleteResult {
  status: "reward_pending" | "completed";
  reward: Reward | null;
  already_completed: boolean;
  tour: Tour;
}

export interface AvatarResult {
  avatar_key: string;
  reward: Reward | null;
  tour: Tour;
}

export interface Asset {
  id: string;
  asset_type: string;
  source_lesson_id: string;
  source_action_key: string;
  content: Record<string, unknown>;
  status: "draft" | "approved" | "published";
  origin: "user" | "ai";
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface ProfilePage {
  email: string;
  profile: Profile;
  xp_total: number;
  rank: Rank;
  ranks: RankStep[];
  streak: Streak;
  achievements: Achievement[];
  assets: Asset[];
  completed_count: number;
  total_count: number;
  avatars: string[];
}

export interface Daily {
  day: string;
  challenge: { key: string; title: string; intro: string | null; xp: number; action: LessonAction } | null;
  completed: boolean;
  streak: Streak;
}

export interface DailySubmitResult {
  daily: Daily;
  xp_awarded: number;
  xp_total: number;
  rank: Rank;
  rank_up: boolean;
}
