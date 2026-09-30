"use client";
/**
 * Officer agent chat. POST /agent/ask with the UI language; the backend's
 * TOOL_REGISTRY has no approve/send tool (AC7), so nothing here can execute
 * anything. At most it surfaces a draft order to review on the Orders page.
 */
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, PaperPlaneRight, Robot, ShieldCheck, UserCircle } from "@phosphor-icons/react";
import { Empty, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useI18n } from "@/lib/i18n";

interface ChatEntry {
  id: string;
  role: "officer" | "agent";
  text: string;
  draft?: boolean;
}

export default function AgentPage() {
  const { t, lang } = useI18n();
  const { user, ready } = useAuth();
  const [question, setQuestion] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [asking, setAsking] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Block body on purpose: newer browsers return a Promise from scroll methods,
    // which React would try to call as the effect's cleanup.
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [entries, asking]);

  async function ask(q: string = question) {
    if (!q.trim() || asking) return;
    const id = `q-${Date.now()}`;
    setEntries((prev) => [...prev, { id, role: "officer", text: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const answer = await api.askAgent(q, lang);
      setEntries((prev) => [...prev, { id: `${id}-a`, role: "agent", text: answer.text, draft: !!answer.draft_order_id }]);
    } catch (err) {
      setEntries((prev) => [...prev, { id: `${id}-err`, role: "agent", text: t("agent_error", { error: (err as Error).message }) }]);
    } finally {
      setAsking(false);
    }
  }

  if (!ready) return null;
  if (!user) {
    return (
      <div className="mx-auto max-w-xl pt-8">
        <Empty icon={<Robot size={22} />} title={t("agent_title")} hint={t("agent_signin")} />
      </div>
    );
  }

  const suggestions = [t("agent_q_risk"), t("agent_q_explain"), t("agent_q_propose")];

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={t("agent_title")} sub={t("agent_sub")} />

      <div className="card flex flex-col overflow-hidden">
        <div className="flex h-[min(56dvh,560px)] flex-col gap-4 overflow-y-auto p-4 md:p-5" data-testid="agent-chat" aria-live="polite">
          {entries.length === 0 && (
            <div className="muted m-auto flex max-w-sm flex-col items-center gap-3 text-center text-sm">
              <span className="grid h-11 w-11 place-items-center rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">
                <ShieldCheck size={22} weight="duotone" />
              </span>
              {t("agent_empty")}
            </div>
          )}
          <AnimatePresence initial={false}>
            {entries.map((e) => (
              <motion.div
                key={e.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className={`flex gap-2.5 ${e.role === "officer" ? "flex-row-reverse" : ""}`}
              >
                <span className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full ${e.role === "officer" ? "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300" : "bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950"}`}>
                  {e.role === "officer" ? <UserCircle size={18} /> : <Robot size={16} weight="fill" />}
                </span>
                <div
                  className={`max-w-[80%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    e.role === "officer"
                      ? "rounded-tr-sm bg-teal-700 text-white dark:bg-teal-600"
                      : "rounded-tl-sm bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100"
                  }`}
                >
                  <span className="sr-only">{e.role === "officer" ? t("agent_you") : t("agent_name")}: </span>
                  {e.text}
                  {e.draft && (
                    <Link href="/orders" className="mt-2 flex items-center gap-1 font-medium text-teal-700 hover:underline dark:text-teal-300">
                      {t("agent_review_drafts")} <ArrowRight size={14} />
                    </Link>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {asking && (
            <div className="flex items-center gap-2.5" aria-live="polite">
              <span className="grid h-8 w-8 place-items-center rounded-full bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950">
                <Robot size={16} weight="fill" />
              </span>
              <span className="muted flex items-center gap-2 rounded-xl bg-zinc-100 px-3.5 py-2.5 text-sm dark:bg-zinc-800">
                <span className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.span
                      key={i}
                      className="h-1.5 w-1.5 rounded-full bg-zinc-400"
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                    />
                  ))}
                </span>
                {t("agent_thinking")}
              </span>
            </div>
          )}
          <div ref={bottom} />
        </div>

        <div className="border-t border-zinc-200/80 p-3 dark:border-zinc-800 md:p-4">
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.map((q) => (
              <button key={q} className="chip" onClick={() => ask(q)} disabled={asking}>
                {q}
              </button>
            ))}
          </div>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              ask();
            }}
          >
            <label className="sr-only" htmlFor="agent-input">{t("agent_placeholder")}</label>
            <input
              id="agent-input"
              name="question"
              autoComplete="off"
              className="field flex-1"
              placeholder={t("agent_placeholder")}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              data-testid="agent-input"
            />
            <button type="submit" className="btn-primary" disabled={asking} data-testid="agent-ask">
              <PaperPlaneRight size={16} weight="fill" /> {t("agent_ask")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
