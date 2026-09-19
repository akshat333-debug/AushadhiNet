"use client";
/**
 * WhatsApp simulator (project.md's Twilio-sandbox-plus-simulator
 * decision, modular-plan.md step 40): posts to the same
 * /simulator/message endpoint that funnels through the identical
 * publish_inbound_message() as the real Twilio webhook.
 */
import { useState } from "react";
import { api } from "@/lib/api";

interface ChatMessage {
  id: string;
  from: "user" | "system";
  text: string;
}

export default function SimulatorPage() {
  const [phone, setPhone] = useState("+911234567890");
  const [body, setBody] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  async function send() {
    if (!body.trim()) return;
    setSending(true);
    const messageId = `sim-${Date.now()}`;
    setMessages((prev) => [...prev, { id: messageId, from: "user", text: body }]);
    try {
      await api.simulatorSend({ from_phone: `whatsapp:${phone}`, body, message_id: messageId });
      setMessages((prev) => [...prev, { id: `${messageId}-ack`, from: "system", text: "Queued for processing." }]);
    } catch (err) {
      setMessages((prev) => [...prev, { id: `${messageId}-err`, from: "system", text: `Error: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
      setBody("");
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-4 text-xl font-semibold">WhatsApp Simulator</h1>
      <label className="mb-2 block text-sm">
        From (phone)
        <input
          className="mt-1 w-full rounded border px-2 py-1"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          data-testid="sim-phone"
        />
      </label>
      <div className="mb-4 h-64 overflow-y-auto rounded border bg-white p-2" data-testid="sim-messages">
        {messages.map((m) => (
          <div key={m.id} className={m.from === "user" ? "text-right" : "text-left text-gray-500"}>
            <span className="inline-block rounded bg-green-100 px-2 py-1 my-1">{m.text}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border px-2 py-1"
          placeholder="e.g. ORS 50"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          data-testid="sim-input"
        />
        <button className="rounded bg-green-600 px-4 py-1 text-white disabled:opacity-50" onClick={send} disabled={sending} data-testid="sim-send">
          Send
        </button>
      </div>
    </div>
  );
}
