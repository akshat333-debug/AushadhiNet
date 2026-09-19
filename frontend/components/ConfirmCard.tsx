"use client";
/**
 * Renders a confirmation card (backend/ingest/cards.py's ConfirmationCard)
 * for the officer PWA / simulator to display when a low-confidence field
 * needs a one-tap confirm or correction.
 */
export interface ConfirmationCardData {
  record_id: string;
  text: string;
  buttons: string[];
}

export default function ConfirmCard({ card, onRespond }: { card: ConfirmationCardData; onRespond: (button: string) => void }) {
  return (
    <div className="rounded border bg-yellow-50 p-3" data-testid={`confirm-card-${card.record_id}`}>
      <p className="mb-2 text-sm">{card.text}</p>
      <div className="flex gap-2">
        {card.buttons.map((b) => (
          <button key={b} className="rounded bg-yellow-600 px-3 py-1 text-xs text-white" onClick={() => onRespond(b)}>
            {b}
          </button>
        ))}
      </div>
    </div>
  );
}
