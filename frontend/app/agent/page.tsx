"use client";
/**
 * Officer agent chat (modular-plan.md step 43). Calls POST /agent/ask;
 * the backend's TOOL_REGISTRY has no approve/send tool (AC7), so nothing
 * this page can trigger executes anything -- it only ever surfaces text
 * and, at most, a draft order id to review on the Orders page.
 */
import { useState } from "react";
import { api } from "@/lib/api";

interface ChatEntry {
  id: string;
  role: "officer" | "agent";
  text: string;
}

export default function AgentPage() {
  const [question, setQuestion] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [asking, setAsking] = useState(false);

  async function ask() {
    if (!question.trim()) return;
    const id = `q-${Date.now()}`;
    setEntries((prev) => [...prev, { id, role: "officer", text: question }]);
    setAsking(true);
    try {
      const answer = await api.askAgent(question);
      setEntries((prev) => [...prev, { id: `${id}-a`, role: "agent", text: answer.text }]);
    } catch (err) {
      setEntries((prev) => [...prev, { id: `${id}-err`, role: "agent", text: `Error: ${(err as Error).message}` }]);
    } finally {
      setAsking(false);
      setQuestion("");
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-4 text-xl font-semibold">Ask the Officer Agent</h1>
      <div className="mb-4 space-y-2 rounded border bg-white p-3" data-testid="agent-chat">
        {entries.map((e) => (
          <p key={e.id} className={e.role === "officer" ? "font-medium" : "text-gray-600"}>
            {e.role === "officer" ? "You: " : "Agent: "}
            {e.text}
          </p>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border px-2 py-1"
          placeholder="e.g. why is F1 at risk for ors?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          data-testid="agent-input"
        />
        <button className="rounded bg-blue-600 px-4 py-1 text-white disabled:opacity-50" onClick={ask} disabled={asking} data-testid="agent-ask">
          Ask
        </button>
      </div>
    </div>
  );
}
