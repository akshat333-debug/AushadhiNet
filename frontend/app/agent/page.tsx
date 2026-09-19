"use client";
/**
 * Officer agent chat (modular-plan.md step 43). Calls POST /agent/ask;
 * the backend's TOOL_REGISTRY has no approve/send tool (AC7), so nothing
 * this page can trigger executes anything -- it only ever surfaces text
 * and, at most, a draft order id to review on the Orders page.
 */
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

interface ChatEntry {
  id: string;
  role: "officer" | "agent";
  text: string;
  draft?: boolean;
}

const EXAMPLES = ["Which facilities are at risk?", "Why is MH-0000221 at risk for ORS?", "Propose transfers"];

export default function AgentPage() {
  const [question, setQuestion] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [asking, setAsking] = useState(false);
  const { user, ready } = useAuth();

  async function ask(q: string = question) {
    if (!q.trim()) return;
    const id = `q-${Date.now()}`;
    setEntries((prev) => [...prev, { id, role: "officer", text: q }]);
    setAsking(true);
    try {
      const answer = await api.askAgent(q);
      setEntries((prev) => [...prev, { id: `${id}-a`, role: "agent", text: answer.text, draft: !!answer.draft_order_id }]);
    } catch (err) {
      setEntries((prev) => [...prev, { id: `${id}-err`, role: "agent", text: `Error: ${(err as Error).message}` }]);
    } finally {
      setAsking(false);
      setQuestion("");
    }
  }

  if (!ready) return null;
  if (!user) return <p className="text-sm text-gray-500">Sign in as an officer (top right) to use the agent.</p>;

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-4 text-xl font-semibold">Ask the Officer Agent</h1>
      <div className="mb-3 flex flex-wrap gap-2">
        {EXAMPLES.map((q) => (
          <button key={q} className="rounded border px-2 py-0.5 text-xs" onClick={() => ask(q)} disabled={asking}>
            {q}
          </button>
        ))}
      </div>
      <div className="mb-4 space-y-2 rounded border bg-white p-3" data-testid="agent-chat">
        {entries.map((e) => (
          <p key={e.id} className={e.role === "officer" ? "font-medium" : "text-gray-600"}>
            {e.role === "officer" ? "You: " : "Agent: "}
            {e.text}
            {e.draft && (
              <a className="ml-1 underline" href="/orders">
                Review drafts
              </a>
            )}
          </p>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border px-2 py-1"
          placeholder="Ask about stock, risk or transfers"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          data-testid="agent-input"
        />
        <button className="rounded bg-blue-600 px-4 py-1 text-white disabled:opacity-50" onClick={() => ask()} disabled={asking} data-testid="agent-ask">
          Ask
        </button>
      </div>
    </div>
  );
}
