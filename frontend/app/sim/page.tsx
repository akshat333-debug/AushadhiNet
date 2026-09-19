"use client";
/**
 * WhatsApp simulator (project.md's Twilio-sandbox-plus-simulator
 * decision): posts to /simulator/message, which funnels through the same
 * publish_inbound_message() as the real Twilio webhook, and shows what
 * the system would have sent back by polling /simulator/outbox.
 */
import { useEffect, useRef, useState } from "react";
import ConfirmCard from "@/components/ConfirmCard";
import { api, Contact, OutboxMessage } from "@/lib/api";

interface Sent {
  id: string;
  text: string;
  repliesBefore: number;
}

type Bubble = { key: string; mine: boolean; text: string; buttons: string[] };

export default function SimulatorPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [phone, setPhone] = useState("");
  const [body, setBody] = useState("");
  const [sent, setSent] = useState<Sent[]>([]);
  const [replies, setReplies] = useState<OutboxMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .simulatorContacts()
      .then((c) => {
        setContacts(c);
        if (c.length) setPhone(c[0].phone);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!phone) return;
    const load = () => api.simulatorOutbox(phone).then(setReplies).catch(() => undefined);
    load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [phone]);

  async function send(text: string) {
    if (!text.trim() || !phone) return;
    setSending(true);
    setError(null);
    const id = `sim-${Date.now()}`;
    try {
      const before = replies.length;
      await api.simulatorSend({ from_phone: phone, body: text, message_id: id });
      setSent((prev) => [...prev, { id, text, repliesBefore: before }]);
      setReplies(await api.simulatorOutbox(phone));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
      setBody("");
    }
  }

  const facility = contacts.find((c) => c.phone === phone);
  const thread: Bubble[] = [];
  for (let i = 0; i <= replies.length; i++) {
    sent.filter((s) => s.repliesBefore === i).forEach((s) => thread.push({ key: s.id, mine: true, text: s.text, buttons: [] }));
    const r = replies[i];
    if (r) thread.push({ key: `r-${r.seq}`, mine: false, text: r.body, buttons: r.buttons });
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-4 text-xl font-semibold">WhatsApp Simulator</h1>
      <label className="mb-2 block text-sm">
        Sending as
        <select
          className="mt-1 w-full rounded border px-2 py-1"
          value={phone}
          onChange={(e) => {
            setPhone(e.target.value);
            setSent([]);
          }}
          data-testid="sim-phone"
        >
          {contacts.map((c) => (
            <option key={c.phone} value={c.phone}>
              {c.name} ({c.facility_id})
            </option>
          ))}
        </select>
      </label>
      {facility && <p className="mb-2 text-xs text-gray-500">{facility.phone}</p>}
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
      <div className="mb-4 h-72 space-y-1 overflow-y-auto rounded border bg-white p-2" data-testid="sim-messages">
        {thread.length === 0 && <p className="text-sm text-gray-400">Try &ldquo;ORS 50&rdquo; or &ldquo;Zinc 0&rdquo;.</p>}
        {thread.map((m) =>
          m.buttons.length ? (
            <ConfirmCard
              key={m.key}
              card={{ record_id: m.key, text: m.text, buttons: m.buttons }}
              onRespond={(b) => (b === "Confirm" ? send("YES") : inputRef.current?.focus())}
            />
          ) : (
            <div key={m.key} className={m.mine ? "text-right" : "text-left"}>
              <span className={`my-1 inline-block rounded px-2 py-1 text-sm ${m.mine ? "bg-green-100" : "bg-gray-100"}`}>{m.text}</span>
            </div>
          ),
        )}
      </div>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          className="flex-1 rounded border px-2 py-1"
          placeholder="e.g. ORS 50"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(body)}
          data-testid="sim-input"
        />
        <button
          className="rounded bg-green-600 px-4 py-1 text-white disabled:opacity-50"
          onClick={() => send(body)}
          disabled={sending || !phone}
          data-testid="sim-send"
        >
          Send
        </button>
      </div>
    </div>
  );
}
