import { defineArrayMember, defineField, defineType } from "sanity";
import { actionTypes } from "./actions";
import { blockTypes } from "./blocks";
import { keyField, slugField } from "./shared";

const THEMES = ["yellow", "blue", "violet", "green", "orange", "pink"];

export const documentTypes = [
  defineType({
    name: "domain",
    title: "Domain",
    type: "document",
    fields: [defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }), slugField()],
  }),

  defineType({
    name: "learningPath",
    title: "Learning path",
    type: "document",
    fields: [
      defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
      slugField(),
      defineField({ name: "domain", title: "Domain", type: "reference", to: [{ type: "domain" }], validation: (rule) => rule.required() }),
      defineField({
        name: "chapters",
        title: "Chapters (in order)",
        type: "array",
        of: [defineArrayMember({ type: "reference", to: [{ type: "chapter" }] })],
        validation: (rule) => rule.required().min(1).unique(),
      }),
      defineField({
        name: "avatars",
        title: "Avatars",
        description: "Keys of the characters learners can choose. Each key must exist in the web app's avatar set.",
        type: "array",
        of: [{ type: "string" }],
        options: { list: ["fox", "owl", "cat", "bear", "frog", "robot"] },
        validation: (rule) => rule.required().min(1),
      }),
      defineField({
        name: "moreComing",
        title: "What is coming next",
        description: "One line shown after the last level on the map. The path is open-ended.",
        type: "string",
      }),
      defineField({
        name: "dailyChallenges",
        title: "Daily challenges",
        description: "A pool of two-minute tasks. Each learner gets one per day, in rotation. XP is paid once per day.",
        type: "array",
        of: [
          {
            type: "object",
            name: "dailyChallenge",
            fields: [
              keyField(),
              defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
              defineField({ name: "intro", title: "Intro", type: "string" }),
              defineField({ name: "xp", title: "XP", type: "number", initialValue: 10, validation: (rule) => rule.required().min(1).max(100) }),
              defineField({
                name: "action",
                title: "Task",
                description: "Exactly one. Real-world tasks work best: something to do outside the app, a set number of times.",
                type: "array",
                of: ["externalTaskAction", "acknowledgeAction", "textSubmissionAction", "quizAction"].map((type) => defineArrayMember({ type })),
                validation: (rule) => rule.required().length(1),
              }),
            ],
            preview: { select: { title: "title", subtitle: "key" } },
          },
        ],
      }),
      defineField({
        name: "achievements",
        title: "Achievements",
        description: "Defined as data. The backend decides when a trigger is met.",
        type: "array",
        of: [
          {
            type: "object",
            name: "achievement",
            fields: [
              keyField(),
              defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
              defineField({ name: "description", title: "Description", type: "string", validation: (rule) => rule.required() }),
              defineField({
                name: "trigger",
                title: "Trigger",
                type: "object",
                validation: (rule) => rule.required(),
                fields: [
                  defineField({
                    name: "type",
                    title: "When",
                    type: "string",
                    options: {
                      list: [
                        { title: "A lesson is completed", value: "lesson_completed" },
                        { title: "A number of lessons are completed", value: "lessons_completed_count" },
                        { title: "An asset is saved", value: "asset_created" },
                      ],
                    },
                    validation: (rule) => rule.required(),
                  }),
                  defineField({
                    name: "lesson",
                    title: "Lesson",
                    type: "reference",
                    to: [{ type: "lesson" }],
                    hidden: ({ parent }) => parent?.type !== "lesson_completed",
                  }),
                  defineField({ name: "count", title: "Number of lessons", type: "number", hidden: ({ parent }) => parent?.type !== "lessons_completed_count" }),
                  defineField({ name: "assetType", title: "Asset type", type: "string", hidden: ({ parent }) => parent?.type !== "asset_created" }),
                ],
              }),
            ],
            preview: { select: { title: "title", subtitle: "key" } },
          },
        ],
      }),
    ],
  }),

  defineType({
    name: "chapter",
    title: "Chapter",
    type: "document",
    fields: [
      defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
      slugField(),
      defineField({ name: "theme", title: "Colour theme", type: "string", options: { list: THEMES }, validation: (rule) => rule.required() }),
      defineField({ name: "tier", title: "Tier label", description: "For example Basics, Core, Advanced.", type: "string", validation: (rule) => rule.required() }),
      defineField({ name: "blurb", title: "Blurb", type: "text", rows: 2, validation: (rule) => rule.required() }),
      defineField({
        name: "lessons",
        title: "Lessons (in order)",
        type: "array",
        of: [defineArrayMember({ type: "reference", to: [{ type: "lesson" }] })],
        validation: (rule) => rule.required().min(1).unique(),
      }),
    ],
    preview: { select: { title: "title", subtitle: "tier" } },
  }),

  defineType({
    name: "lesson",
    title: "Lesson",
    type: "document",
    groups: [
      { name: "map", title: "Journey map", default: true },
      { name: "content", title: "Lesson content" },
    ],
    fields: [
      defineField({ name: "title", title: "Title", type: "string", group: "map", validation: (rule) => rule.required() }),
      { ...slugField(), group: "map" },
      defineField({ name: "minutes", title: "Minutes", type: "number", group: "map", validation: (rule) => rule.required().min(1).max(600) }),
      defineField({
        name: "xp",
        title: "XP reward",
        description: "Paid once, by the backend, when the lesson is completed.",
        type: "number",
        group: "map",
        validation: (rule) => rule.required().min(1).max(1000),
      }),
      defineField({ name: "summary", title: "Summary", type: "text", rows: 2, group: "map", validation: (rule) => rule.required() }),
      defineField({ name: "output", title: "What the learner finishes with", type: "text", rows: 2, group: "map", validation: (rule) => rule.required() }),
      defineField({
        name: "parts",
        title: "Parts",
        type: "array",
        group: "map",
        of: [
          {
            type: "object",
            name: "lessonPart",
            fields: [
              defineField({ name: "kind", title: "Kind", type: "string", options: { list: ["Read", "Practice", "Create"] }, validation: (rule) => rule.required() }),
              defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
              defineField({ name: "minutes", title: "Minutes", type: "number", validation: (rule) => rule.required().min(1) }),
            ],
            preview: { select: { title: "title", subtitle: "kind" } },
          },
        ],
      }),
      defineField({
        name: "blocks",
        title: "Blocks",
        description: "Leave empty to show the lesson on the map as “coming soon”.",
        type: "array",
        group: "content",
        of: blockTypes.map((type) => defineArrayMember({ type: type.name })),
      }),
      defineField({
        name: "actions",
        title: "Actions",
        description: "Define each action once here, then place it in a block by its key.",
        type: "array",
        group: "content",
        of: actionTypes.map((type) => defineArrayMember({ type: type.name })),
      }),
    ],
    preview: { select: { title: "title", subtitle: "slug.current" } },
  }),
];
