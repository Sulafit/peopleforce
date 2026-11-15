import type { ReactNode } from "react";
import Markdown from "react-markdown";
import type { Block } from "@/lib/api/types";

const CALLOUT_LABEL = { info: "Note", tip: "Example", warning: "Keep in mind" } as const;

/** CMS text is rendered as Markdown with raw HTML disabled (react-markdown's default). */
function Prose({ children }: { children: string }) {
  return (
    <div className="prose">
      <Markdown
        components={{
          a: ({ href, children: label }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {label}
            </a>
          ),
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}

/** Renders one content block. `renderActions` places a group's actions (by key) inside its card. */
export function BlockView({
  block,
  renderActions,
  tourAnchor,
}: {
  block: Block;
  renderActions: (keys: string[]) => ReactNode;
  tourAnchor?: string;
}) {
  switch (block.type) {
    case "markdown":
      return (
        <section className="lesson-block">
          {block.title && <h2 className="lesson-block__title">{block.title}</h2>}
          <Prose>{block.body}</Prose>
        </section>
      );
    case "callout":
      return (
        <aside className={`callout callout--${block.tone}`}>
          <span className="cap">{block.title ?? CALLOUT_LABEL[block.tone]}</span>
          <Prose>{block.body}</Prose>
        </aside>
      );
    case "youtube":
      return (
        <figure className="video">
          <div className="video__frame">
            <iframe
              src={`https://www.youtube-nocookie.com/embed/${block.video_id}`}
              title={block.title}
              loading="lazy"
              allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              referrerPolicy="strict-origin-when-cross-origin"
            />
          </div>
          <figcaption className="hint">{block.title}</figcaption>
        </figure>
      );
    case "resources":
      return (
        <section className="side-card">
          <h2 className="cap muted">{block.title ?? "Resources"}</h2>
          <ul className="resources">
            {block.links.map((link) => (
              <li key={link.url}>
                <a href={link.url} target="_blank" rel="noopener noreferrer">
                  {link.label}
                </a>
                {link.description && <span className="hint"> · {link.description}</span>}
              </li>
            ))}
          </ul>
        </section>
      );
    case "action_group":
    case "quiz":
    case "ai_feedback":
      return (
        <section className="card" data-tour={tourAnchor}>
          {block.title && <h2 className="card__title">{block.title}</h2>}
          {block.intro && <p className="card__intro">{block.intro}</p>}
          {renderActions(block.action_keys)}
        </section>
      );
    default:
      return null;
  }
}
