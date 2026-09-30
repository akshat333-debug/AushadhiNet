"use client";
/**
 * A confirmation card (backend/ingest/cards.py): a low-confidence field is
 * never saved silently; the reporter confirms it or sends a correction.
 * Buttons arrive already localized, so the first one is always "confirm".
 */
import { Question } from "@phosphor-icons/react";

export interface ConfirmationCardData {
  record_id: string;
  text: string;
  buttons: string[];
}

export default function ConfirmCard({ card, onRespond }: { card: ConfirmationCardData; onRespond: (button: string, index: number) => void }) {
  return (
    <div className="max-w-[88%] overflow-hidden rounded-lg rounded-tl-none bg-white shadow-sm dark:bg-zinc-800" data-testid={`confirm-card-${card.record_id}`}>
      <p className="flex gap-2 px-3 py-2 text-[13.5px] leading-snug text-zinc-900 dark:text-zinc-100">
        <Question size={16} weight="fill" className="mt-0.5 shrink-0 text-amber-500" />
        <span>{card.text}</span>
      </p>
      <div className="grid border-t border-zinc-200 dark:border-zinc-700" style={{ gridTemplateColumns: `repeat(${card.buttons.length}, 1fr)` }}>
        {card.buttons.map((b, i) => (
          <button
            key={b}
            className="border-zinc-200 px-2 py-2 text-sm font-medium text-teal-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-teal-300 dark:hover:bg-zinc-700/50 [&:not(:first-child)]:border-l"
            onClick={() => onRespond(b, i)}
          >
            {b}
          </button>
        ))}
      </div>
    </div>
  );
}
