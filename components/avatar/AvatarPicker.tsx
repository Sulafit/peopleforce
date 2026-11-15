"use client";

import { useState } from "react";
import { AVATARS, Avatar, avatarLabel } from "@/components/avatar/avatars";
import { Modal } from "@/components/ui/Modal";
import { useSelectAvatar } from "@/lib/api/hooks";
import type { AvatarResult } from "@/lib/api/types";

interface AvatarPickerProps {
  avatars: string[];
  /** Tour wording when the first-run tour is active, neutral wording otherwise. */
  message: string;
  onSelected: (result: AvatarResult) => void;
  /** Pre-selected character (when changing an existing one). */
  current?: string | null;
  /** Makes the dialog dismissable. Omitted while a reward is waiting for the first choice. */
  onClose?: () => void;
  eyebrow?: string;
}

/**
 * Shown while a lesson reward is waiting for an avatar. Not dismissable: choosing takes one click and
 * the saved lesson is safe either way (leaving and coming back reopens this dialog).
 */
export function AvatarPicker({ avatars, message, onSelected, current = null, onClose, eyebrow = "Lesson saved" }: AvatarPickerProps) {
  const [choice, setChoice] = useState<string | null>(current);
  const select = useSelectAvatar();
  const options = avatars.filter((key) => key in AVATARS);

  return (
    <Modal labelledBy="avatar-title" theme="violet" onClose={onClose}>
      <span className="cap modal__eyebrow">{eyebrow}</span>
      <h2 id="avatar-title" className="modal__title">
        {message}
      </h2>
      <div className="avatar-grid" role="radiogroup" aria-label="Characters">
        {options.map((key) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={choice === key}
            className={`avatar-option${choice === key ? " is-selected" : ""}`}
            onClick={() => setChoice(key)}
          >
            <Avatar avatarKey={key} size={72} />
            <span>{avatarLabel(key)}</span>
          </button>
        ))}
      </div>
      {select.isError && (
        <p className="hint hint--error" role="alert">
          {select.error.message} Your lesson is saved; try again.
        </p>
      )}
      <button
        type="button"
        className="btn btn--primary"
        disabled={!choice || select.isPending}
        onClick={() => choice && select.mutate(choice, { onSuccess: onSelected })}
      >
        {select.isPending ? "Saving…" : "Choose this character"}
      </button>
    </Modal>
  );
}
