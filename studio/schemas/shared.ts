import { defineField } from "sanity";

/** Stable machine keys: lowercase letters, digits, "-" and "_". The API rejects anything else. */
export const KEY_PATTERN = /^[a-z0-9][a-z0-9_-]{0,79}$/;

export function keyField(title = "Key", description = "Stable identifier. Do not change it after learners have used the lesson.") {
  return defineField({
    name: "key",
    title,
    type: "string",
    description,
    validation: (rule) => rule.required().regex(KEY_PATTERN, { name: "key" }),
  });
}

export function slugField(source = "title") {
  return defineField({
    name: "slug",
    title: "ID (slug)",
    type: "slug",
    description: "Stable identifier used by the app. Do not change it after publishing.",
    options: { source, maxLength: 80 },
    validation: (rule) => rule.required(),
  });
}

/** Sanity has no map type, so maps are edited as key/value rows. Keys are quiz specialization values. */
export const SPECIALIZATIONS = [
  { title: "Default (fallback)", value: "default" },
  { title: "Websites", value: "websites" },
  { title: "Web applications", value: "web_apps" },
  { title: "Mobile applications", value: "mobile_apps" },
  { title: "Backend / APIs", value: "backend" },
  { title: "Automation", value: "automation" },
  { title: "Not sure", value: "not_sure" },
];

export function bySpecializationField(name: string, title: string, description: string, rows = 2) {
  return defineField({
    name,
    title,
    description,
    type: "array",
    of: [
      {
        type: "object",
        name: "specializationText",
        fields: [
          defineField({
            name: "key",
            title: "Specialization",
            type: "string",
            options: { list: SPECIALIZATIONS },
            validation: (rule) => rule.required(),
          }),
          defineField({ name: "value", title: "Text", type: "text", rows, validation: (rule) => rule.required() }),
        ],
        preview: { select: { title: "key", subtitle: "value" } },
      },
    ],
  });
}
