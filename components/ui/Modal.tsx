"use client";

import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  labelledBy: string;
  children: ReactNode;
  /** Omit to make the dialog non-dismissable (the step has to be finished). */
  onClose?: () => void;
  theme?: string;
}

/** Centered dialog in the app's card style. Focus moves in on open and Escape closes it when allowed. */
export function Modal({ labelledBy, children, onClose, theme = "yellow" }: ModalProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && onClose) onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previous?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose?.()}>
      <div ref={ref} className={`modal t-${theme}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy} tabIndex={-1}>
        {children}
      </div>
    </div>
  );
}
