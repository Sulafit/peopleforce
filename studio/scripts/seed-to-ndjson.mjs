// Converts the bundled seed (api/content/<domain>.json) into Sanity documents (NDJSON), so a new
// dataset starts with the same content the app ships with:
//
//   npm run seed:export > seed.ndjson
//   npx sanity dataset import seed.ndjson production --replace
//
// Imported documents are published (no "drafts." prefix).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const domain = process.argv[2] ?? "software-development";
const path = JSON.parse(readFileSync(join(root, "api", "content", `${domain}.json`), "utf8"));

const BLOCK_TYPES = {
  markdown: "markdownBlock",
  youtube: "youtubeBlock",
  callout: "calloutBlock",
  resources: "resourcesBlock",
  action_group: "actionGroupBlock",
  quiz: "quizBlock",
  ai_feedback: "aiFeedbackBlock",
};
const ACTION_TYPES = {
  acknowledge: "acknowledgeAction",
  text_submission: "textSubmissionAction",
  quiz: "quizAction",
  ai_review: "aiReviewAction",
  save_asset: "saveAssetAction",
  external_task: "externalTaskAction",
};

const slug = (current) => ({ _type: "slug", current });
const ref = (id) => ({ _type: "reference", _ref: id });
const keyed = (items, makeKey) => (items ?? []).map((item, index) => ({ _key: makeKey(item, index), ...item }));
const rows = (map) => Object.entries(map ?? {}).map(([key, value]) => ({ _key: key, key, value }));
const clean = (object) => Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined));

function block(source) {
  return clean({
    _type: BLOCK_TYPES[source.type],
    _key: source.key,
    key: source.key,
    title: source.title,
    body: source.body,
    tone: source.tone,
    intro: source.intro,
    videoId: source.video_id,
    bodyBySpecialization: source.body_by_specialization ? rows(source.body_by_specialization) : undefined,
    links: source.links ? keyed(source.links, (_, index) => `link${index}`) : undefined,
    actionKeys: source.action_keys,
  });
}

function action(source) {
  return clean({
    _type: ACTION_TYPES[source.type],
    _key: source.key,
    key: source.key,
    title: source.title,
    instructions: source.instructions,
    required: source.required,
    dependsOn: source.depends_on,
    confirmLabel: source.confirm_label,
    submitLabel: source.submit_label,
    capability: source.capability,
    sourceActionKey: source.source_action_key,
    assetType: source.asset_type,
    passingScore: source.passing_score,
    targetCount: source.target_count,
    unit: source.unit,
    tips: source.tips,
    fields: source.fields?.map((field) =>
      clean({
        _key: field.name,
        name: field.name,
        label: field.label,
        help: field.help,
        placeholder: field.placeholder,
        multiline: field.multiline,
        minLength: field.min_length,
        maxLength: field.max_length,
        examples: field.examples ? rows(field.examples) : undefined,
      }),
    ),
    questions: source.questions?.map((question) => ({
      _key: question.id,
      key: question.id,
      prompt: question.prompt,
      explanation: question.explanation,
      correctOptionId: question.correct_option_id,
      options: question.options.map((option) => ({ _key: option.id, key: option.id, label: option.label })),
    })),
  });
}

const documents = [{ _id: `domain.${path.domain}`, _type: "domain", title: "Software Development", slug: slug(path.domain) }];

for (const chapter of path.chapters) {
  for (const lesson of chapter.lessons) {
    documents.push(
      clean({
        _id: `lesson.${lesson.id}`,
        _type: "lesson",
        title: lesson.title,
        slug: slug(lesson.id),
        minutes: lesson.minutes,
        xp: lesson.xp,
        summary: lesson.summary,
        output: lesson.output,
        parts: keyed(lesson.parts, (_, index) => `part${index}`),
        blocks: lesson.content?.blocks.map(block),
        actions: lesson.content?.actions.map(action),
      }),
    );
  }
  documents.push({
    _id: `chapter.${chapter.id}`,
    _type: "chapter",
    title: chapter.title,
    slug: slug(chapter.id),
    theme: chapter.theme,
    tier: chapter.tier,
    blurb: chapter.blurb,
    lessons: chapter.lessons.map((lesson) => ({ _key: lesson.id, ...ref(`lesson.${lesson.id}`) })),
  });
}

documents.push({
  _id: `path.${path.id}`,
  _type: "learningPath",
  title: path.title,
  slug: slug(path.id),
  domain: ref(`domain.${path.domain}`),
  avatars: path.avatars,
  moreComing: path.more_coming,
  dailyChallenges: (path.daily_challenges ?? []).map((challenge) =>
    clean({
      _key: challenge.key,
      key: challenge.key,
      title: challenge.title,
      intro: challenge.intro,
      xp: challenge.xp,
      action: [action(challenge.action)],
    }),
  ),
  chapters: path.chapters.map((chapter) => ({ _key: chapter.id, ...ref(`chapter.${chapter.id}`) })),
  achievements: path.achievements.map((achievement) => ({
    _key: achievement.key,
    key: achievement.key,
    title: achievement.title,
    description: achievement.description,
    trigger: clean({
      type: achievement.trigger.type,
      lesson: achievement.trigger.lesson_id ? ref(`lesson.${achievement.trigger.lesson_id}`) : undefined,
      count: achievement.trigger.count,
      assetType: achievement.trigger.asset_type,
    }),
  })),
});

process.stdout.write(documents.map((document) => JSON.stringify(document)).join("\n") + "\n");
