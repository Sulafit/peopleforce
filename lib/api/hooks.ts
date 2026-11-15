"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { ApiError, api } from "@/lib/api/client";
import type {
  ActionSubmitResult,
  AvatarResult,
  CompleteResult,
  Daily,
  DailySubmitResult,
  Journey,
  JourneyPreview,
  Lesson,
  MagicLinkSent,
  Me,
  OnboardingDraft,
  OnboardingQuiz,
  ProfilePage,
  QuizAnswer,
  Tour,
  TourEvent,
} from "@/lib/api/types";

export const keys = {
  me: ["me"] as const,
  quiz: ["onboarding", "quiz"] as const,
  preview: ["onboarding", "preview"] as const,
  journey: ["journey"] as const,
  daily: ["daily"] as const,
  profile: ["profile"] as const,
  lesson: (id: string) => ["lesson", id] as const,
};

/** Expected API answers (401, 403, 409...) are final; only transport and server errors are retried. */
const retry = (count: number, error: Error) => count < 2 && error instanceof ApiError && (error.status === 0 || error.status >= 500);

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: () => api.get<Me>("/me"), retry, staleTime: 60_000 });
}

export function useOnboardingQuiz() {
  return useQuery({ queryKey: keys.quiz, queryFn: () => api.get<OnboardingQuiz>("/onboarding/quiz"), retry });
}

export function useSaveAnswer() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { question_id: string; value: QuizAnswer }) => api.put<OnboardingDraft>("/onboarding/answers", input),
    onSuccess: (draft) => {
      client.setQueryData<OnboardingQuiz>(keys.quiz, (old) => (old ? { ...old, draft } : old));
      client.removeQueries({ queryKey: keys.preview });
    },
  });
}

export function useCompleteQuiz() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<JourneyPreview>("/onboarding/complete"),
    onSuccess: (preview) => client.setQueryData(keys.preview, preview),
  });
}

export function usePreview() {
  return useQuery({ queryKey: keys.preview, queryFn: () => api.get<JourneyPreview>("/onboarding/preview"), retry });
}

export function useRequestMagicLink() {
  return useMutation({ mutationFn: (email: string) => api.post<MagicLinkSent>("/auth/magic-link", { email }) });
}

export function useClaimDraft() {
  return useMutation({ mutationFn: () => api.post<{ redirect: string }>("/onboarding/claim") });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),
    onSuccess: () => client.clear(),
  });
}

export function useJourney() {
  return useQuery({ queryKey: keys.journey, queryFn: () => api.get<Journey>("/journey"), retry });
}

/** Opening a lesson records the start on the server (idempotent) and returns the lesson with the learner's state. */
export function useLesson(lessonId: string) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: keys.lesson(lessonId),
    queryFn: () => api.post<Lesson>(`/journey/lessons/${lessonId}/start`),
    retry,
    refetchOnWindowFocus: false,
  });
  // Opening the first lesson advances the tour on the server; mirror that into the cached journey so
  // the tour does not wait for the next journey refetch.
  const stage = query.data?.tour.stage;
  const status = query.data?.tour.status;
  useEffect(() => {
    if (!stage || !status) return;
    client.setQueryData<Journey>(keys.journey, (old) =>
      old && (old.tour.stage !== stage || old.tour.status !== status) ? { ...old, tour: { stage, status } } : old,
    );
  }, [client, stage, status]);
  return query;
}

export function useSubmitAction(lessonId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { actionKey: string; payload: Record<string, unknown> }) =>
      api.post<ActionSubmitResult>(`/journey/lessons/${lessonId}/actions/${input.actionKey}`, { payload: input.payload }),
    onSuccess: (result) => {
      client.setQueryData<Lesson>(keys.lesson(lessonId), (old) =>
        old ? { ...old, actions: result.actions, completable: result.completable, missing_required: result.missing_required } : old,
      );
      // A finished action counts as activity for today's streak.
      if (result.action.state.completed) {
        void client.invalidateQueries({ queryKey: keys.journey });
        void client.invalidateQueries({ queryKey: keys.profile });
      }
    },
  });
}

export function useCompleteLesson(lessonId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<CompleteResult>(`/journey/lessons/${lessonId}/complete`),
    onSuccess: async () => {
      void client.invalidateQueries({ queryKey: keys.profile });
      await Promise.all([
        client.invalidateQueries({ queryKey: keys.journey }),
        client.invalidateQueries({ queryKey: keys.lesson(lessonId) }),
      ]);
    },
  });
}

export function useSelectAvatar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (avatarKey: string) => api.put<AvatarResult>("/me/avatar", { avatar_key: avatarKey }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: keys.journey });
      void client.invalidateQueries({ queryKey: ["lesson"] });
      void client.invalidateQueries({ queryKey: keys.me });
      void client.invalidateQueries({ queryKey: keys.profile });
    },
  });
}

export function useTourEvent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (event: TourEvent) => api.post<Tour>("/tour/events", { event }),
    onSuccess: (tour) => {
      client.setQueryData<Journey>(keys.journey, (old) =>
        old ? { ...old, tour, last_reward: tour.stage === "first_reward_claimed" ? old.last_reward : null } : old,
      );
      client.setQueriesData<Lesson>({ queryKey: ["lesson"] }, (old) => (old ? { ...old, tour } : old));
    },
  });
}

export function useDaily(enabled: boolean) {
  return useQuery({ queryKey: keys.daily, queryFn: () => api.get<Daily>("/daily"), retry, enabled });
}

export function useSubmitDaily() {
  const client = useQueryClient();
  return useMutation({
    // Same variable shape as lesson actions, so the action components work for both.
    mutationFn: (input: { actionKey: string; payload: Record<string, unknown> }) =>
      api.post<DailySubmitResult>("/daily/submit", { payload: input.payload }),
    onSuccess: (result) => {
      client.setQueryData(keys.daily, result.daily);
      void client.invalidateQueries({ queryKey: keys.journey });
      void client.invalidateQueries({ queryKey: keys.profile });
    },
  });
}

export function useProfilePage() {
  return useQuery({ queryKey: keys.profile, queryFn: () => api.get<ProfilePage>("/profile"), retry });
}

export function useSetTimezone() {
  return useMutation({ mutationFn: (timezone: string) => api.put<void>("/me/timezone", { timezone }) });
}
