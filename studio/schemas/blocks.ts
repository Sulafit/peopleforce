import { defineField, defineType } from "sanity";
import { bySpecializationField, keyField } from "./shared";

/**
 * Content blocks. Type names end in "Block" because Sanity type names are global; the API maps
 * them to its own names (markdownBlock -> markdown, ...). Text supports Markdown and the placeholders
 * {{role}}, {{specialization}}, {{goal}} and {{channel}}. Raw HTML is not rendered.
 */

const actionKeys = defineField({
  name: "actionKeys",
  title: "Actions shown here",
  description: "Keys of actions defined in this lesson's Actions list, in display order.",
  type: "array",
  of: [{ type: "string" }],
  validation: (rule) => rule.required().min(1),
});

function actionPlacement(name: string, title: string) {
  return defineType({
    name,
    title,
    type: "object",
    fields: [
      keyField(),
      defineField({ name: "title", title: "Title", type: "string" }),
      defineField({ name: "intro", title: "Intro", type: "text", rows: 2 }),
      actionKeys,
    ],
    preview: { select: { title: "title", subtitle: "key" } },
  });
}

export const blockTypes = [
  defineType({
    name: "markdownBlock",
    title: "Text (Markdown)",
    type: "object",
    fields: [
      keyField(),
      defineField({ name: "title", title: "Heading", type: "string" }),
      defineField({ name: "body", title: "Body", type: "text", rows: 10, validation: (rule) => rule.required() }),
    ],
    preview: { select: { title: "title", subtitle: "body" } },
  }),
  defineType({
    name: "youtubeBlock",
    title: "YouTube video",
    type: "object",
    fields: [
      keyField(),
      defineField({ name: "title", title: "Title", type: "string", validation: (rule) => rule.required() }),
      defineField({
        name: "videoId",
        title: "YouTube video ID",
        description: "The 11 characters after v= in the video URL.",
        type: "string",
        validation: (rule) => rule.required().regex(/^[A-Za-z0-9_-]{11}$/, { name: "YouTube ID" }),
      }),
    ],
    preview: { select: { title: "title", subtitle: "videoId" } },
  }),
  defineType({
    name: "calloutBlock",
    title: "Callout",
    type: "object",
    fields: [
      keyField(),
      defineField({
        name: "tone",
        title: "Tone",
        type: "string",
        options: { list: ["info", "tip", "warning"], layout: "radio" },
        initialValue: "info",
      }),
      defineField({ name: "title", title: "Label", type: "string" }),
      defineField({ name: "body", title: "Body", type: "text", rows: 4, validation: (rule) => rule.required() }),
      bySpecializationField("bodyBySpecialization", "Body per specialization", "Optional. Replaces the body for learners with that specialization.", 4),
    ],
    preview: { select: { title: "title", subtitle: "body" } },
  }),
  defineType({
    name: "resourcesBlock",
    title: "Resource links",
    type: "object",
    fields: [
      keyField(),
      defineField({ name: "title", title: "Title", type: "string" }),
      defineField({
        name: "links",
        title: "Links",
        type: "array",
        validation: (rule) => rule.required().min(1),
        of: [
          {
            type: "object",
            name: "resourceLink",
            fields: [
              defineField({ name: "label", title: "Label", type: "string", validation: (rule) => rule.required() }),
              defineField({
                name: "url",
                title: "URL",
                type: "url",
                validation: (rule) => rule.required().uri({ scheme: ["https"] }),
              }),
              defineField({ name: "description", title: "Description", type: "string" }),
            ],
          },
        ],
      }),
    ],
    preview: { select: { title: "title", subtitle: "key" } },
  }),
  actionPlacement("actionGroupBlock", "Interactive exercise (action group)"),
  actionPlacement("quizBlock", "Quiz section"),
  actionPlacement("aiFeedbackBlock", "AI feedback section"),
];
