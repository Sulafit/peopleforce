import { defineField, defineType } from "sanity";
import { bySpecializationField, keyField, KEY_PATTERN } from "./shared";

/**
 * Actions: what the learner does. An action only *selects* behaviour the backend implements
 * (its type and its completion rule). Nothing here is executed as code.
 */

const base = [
  keyField(),
  defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
  defineField({ name: "instructions", title: "Instructions", type: "text", rows: 2 }),
  defineField({
    name: "dependsOn",
    title: "Depends on",
    description: "Keys of actions that must be completed first.",
    type: "array",
    of: [{ type: "string" }],
  }),
];

const required = (initialValue: boolean) =>
  defineField({
    name: "required",
    title: "Required to finish the lesson",
    type: "boolean",
    initialValue,
  });

const sourceActionKey = defineField({
  name: "sourceActionKey",
  title: "Source action key",
  description: "Key of the text submission in this lesson whose answers are used.",
  type: "string",
  validation: (rule) => rule.required().regex(KEY_PATTERN, { name: "key" }),
});

const preview = { select: { title: "title", subtitle: "key" } };

export const actionTypes = [
  defineType({
    name: "acknowledgeAction",
    title: "Acknowledge",
    type: "object",
    fields: [...base, required(true), defineField({ name: "confirmLabel", title: "Button label", type: "string", initialValue: "Got it" })],
    preview,
  }),
  defineType({
    name: "textSubmissionAction",
    title: "Text submission",
    type: "object",
    fields: [
      ...base,
      required(true),
      defineField({ name: "submitLabel", title: "Button label", type: "string", initialValue: "Save draft" }),
      defineField({
        name: "fields",
        title: "Form fields",
        type: "array",
        validation: (rule) => rule.required().min(1),
        of: [
          {
            type: "object",
            name: "textField",
            fields: [
              defineField({
                name: "name",
                title: "Field key",
                type: "string",
                validation: (rule) => rule.required().regex(KEY_PATTERN, { name: "key" }),
              }),
              defineField({ name: "label", title: "Question", type: "string", validation: (rule) => rule.required() }),
              defineField({ name: "help", title: "Help text", type: "string" }),
              defineField({ name: "placeholder", title: "Placeholder", type: "string" }),
              defineField({ name: "multiline", title: "Multi-line", type: "boolean", initialValue: true }),
              defineField({ name: "minLength", title: "Minimum characters", type: "number", initialValue: 1, validation: (rule) => rule.min(0).max(5000) }),
              defineField({ name: "maxLength", title: "Maximum characters", type: "number", initialValue: 600, validation: (rule) => rule.min(1).max(5000) }),
              bySpecializationField("examples", "Example answers", "Shown under the field. Add a Default row as the fallback."),
            ],
            preview: { select: { title: "label", subtitle: "name" } },
          },
        ],
      }),
    ],
    preview,
  }),
  defineType({
    name: "quizAction",
    title: "Quiz",
    type: "object",
    fields: [
      ...base,
      required(true),
      defineField({
        name: "passingScore",
        title: "Passing score (0–1)",
        type: "number",
        initialValue: 0.7,
        validation: (rule) => rule.required().greaterThan(0).max(1),
      }),
      defineField({
        name: "questions",
        title: "Questions",
        type: "array",
        validation: (rule) => rule.required().min(1),
        of: [
          {
            type: "object",
            name: "quizQuestion",
            fields: [
              keyField("Question key"),
              defineField({ name: "prompt", title: "Question", type: "string", validation: (rule) => rule.required() }),
              defineField({
                name: "options",
                title: "Options",
                type: "array",
                validation: (rule) => rule.required().min(2),
                of: [
                  {
                    type: "object",
                    name: "quizOption",
                    fields: [
                      keyField("Option key"),
                      defineField({ name: "label", title: "Label", type: "string", validation: (rule) => rule.required() }),
                    ],
                    preview: { select: { title: "label", subtitle: "key" } },
                  },
                ],
              }),
              defineField({
                name: "correctOptionId",
                title: "Correct option key",
                description: "Never sent to the learner's browser before they answer.",
                type: "string",
                validation: (rule) => rule.required(),
              }),
              defineField({ name: "explanation", title: "Explanation (shown after answering)", type: "text", rows: 2 }),
            ],
            preview: { select: { title: "prompt", subtitle: "key" } },
          },
        ],
      }),
    ],
    preview,
  }),
  defineType({
    name: "externalTaskAction",
    title: "Real-world task (counted)",
    type: "object",
    fields: [
      ...base,
      required(true),
      defineField({
        name: "targetCount",
        title: "How many times",
        type: "number",
        validation: (rule) => rule.required().integer().min(1).max(20),
      }),
      defineField({
        name: "unit",
        title: "What one counts as",
        description: "For example: message sent, proposal sent.",
        type: "string",
        validation: (rule) => rule.required(),
      }),
      defineField({ name: "tips", title: "Tips (up to 4)", type: "array", of: [{ type: "string" }], validation: (rule) => rule.max(4) }),
    ],
    preview,
  }),
  defineType({
    name: "aiReviewAction",
    title: "AI feedback",
    type: "object",
    fields: [
      ...base,
      required(false),
      defineField({
        name: "capability",
        title: "AI capability",
        description: "Which backend capability reviews the text. Prompts are managed in Langfuse, not here.",
        type: "string",
        options: {
          list: [
            { title: "Freelance offer feedback", value: "freelance_offer_feedback" },
            { title: "Professional bio feedback", value: "professional_bio_feedback" },
          ],
        },
        validation: (rule) => rule.required(),
      }),
      sourceActionKey,
      defineField({ name: "submitLabel", title: "Button label", type: "string", initialValue: "Get feedback" }),
    ],
    preview,
  }),
  defineType({
    name: "saveAssetAction",
    title: "Save asset to profile",
    type: "object",
    fields: [
      ...base,
      required(true),
      defineField({
        name: "assetType",
        title: "Asset type",
        type: "string",
        options: {
          list: [
            { title: "Freelancer offer", value: "freelancer_offer" },
            { title: "Professional bio", value: "professional_bio" },
            { title: "Portfolio case study", value: "portfolio_case_study" },
          ],
        },
        validation: (rule) => rule.required(),
      }),
      sourceActionKey,
      defineField({ name: "submitLabel", title: "Button label", type: "string", initialValue: "Save to my profile" }),
    ],
    preview,
  }),
];
