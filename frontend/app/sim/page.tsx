"use client";
/**
 * WhatsApp simulator: posts to /simulator/message, which funnels through the
 * same publish_inbound_message() as the real Twilio webhook, and shows what
 * the system sent back by polling /simulator/outbox. The UI language is sent
 * with each message, so replies come back in that language.
 */
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChatCircleText, Checks, Microphone, PaperPlaneRight, ShieldCheck, WhatsappLogo } from "@phosphor-icons/react";
import ConfirmCard from "@/components/ConfirmCard";
import { Notice, PageHeader } from "@/components/ui";
import { api, Contact, OutboxMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Sent {
  id: string;
  text: string;
  repliesBefore: number;
}

type Bubble = { key: string; mine: boolean; text: string; buttons: string[] };

export default function SimulatorPage() {
  const { t, lang } = useI18n();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [phone, setPhone] = useState("");
  const [body, setBody] = useState("");
  const [sent, setSent] = useState<Sent[]>([]);
  const [replies, setReplies] = useState<OutboxMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scroller = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [sent, replies]);

  async function send(text: string, fromInput = false) {
    if (!text.trim() || !phone) return;
    // Clear the box as the message leaves, not when the reply lands: anything typed while
    // a send is in flight must survive (on slow hosting a finally-clear wiped it).
    if (fromInput) setBody("");
    setSending(true);
    setError(null);
    const id = `sim-${Date.now()}`;
    try {
      const before = replies.length;
      await api.simulatorSend({ from_phone: phone, body: text, message_id: id, lang });
      setSent((prev) => [...prev, { id, text, repliesBefore: before }]);
      setReplies(await api.simulatorOutbox(phone));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  const facility = contacts.find((c) => c.phone === phone);
  const thread: Bubble[] = [];
  for (let i = 0; i <= replies.length; i++) {
    sent.filter((s) => s.repliesBefore === i).forEach((s) => thread.push({ key: s.id, mine: true, text: s.text, buttons: [] }));
    const r = replies[i];
    if (r) thread.push({ key: `r-${r.seq}`, mine: false, text: r.body, buttons: r.buttons });
  }

  const examples = [t("sim_example_local"), "IFA 20", t("sim_example_yes")];
  const steps = [t("sim_how_1"), t("sim_how_2"), t("sim_how_3")];

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title={t("sim_title")} sub={t("sim_sub")} />
      {error && <Notice tone="error">{error}</Notice>}

      <div className="grid items-start gap-8 lg:grid-cols-[1fr_400px]">
        <div className="space-y-6 lg:order-1">
          <div className="card p-5">
            <label className="label mb-1.5 block" htmlFor="sim-phone">
              {t("sim_sending_as")}
            </label>
            <select id="sim-phone" className="field" value={phone} onChange={(e) => { setPhone(e.target.value); setSent([]); }} data-testid="sim-phone">
              {contacts.map((c) => (
                <option key={c.phone} value={c.phone}>
                  {c.name} ({c.facility_id})
                </option>
              ))}
            </select>
            {facility && <p className="muted mt-1.5 font-mono text-xs">{facility.phone.replace("whatsapp:", "")}</p>}

            <div className="mt-5">
              <div className="label mb-2">{t("sim_examples")}</div>
              <div className="flex flex-wrap gap-2">
                {examples.map((ex) => (
                  <button key={ex} className="chip" onClick={() => send(ex)} disabled={sending || !phone}>
                    <ChatCircleText size={14} /> {ex}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h2 className="h2 mb-4">{t("sim_how_title")}</h2>
            <ol className="space-y-4">
              {steps.map((step, i) => (
                <li key={step} className="flex gap-3 text-sm">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-teal-50 text-xs font-semibold text-teal-800 dark:bg-teal-950/60 dark:text-teal-300">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Phone */}
        <div className="mx-auto w-full max-w-[400px] rounded-[2.5rem] border-[10px] border-zinc-900 bg-zinc-900 shadow-2xl shadow-zinc-900/20 dark:border-zinc-700 dark:bg-zinc-700 lg:order-2">
          <div className="overflow-hidden rounded-[1.9rem] bg-[#efeae2] dark:bg-zinc-900">
            <div className="flex items-center gap-3 bg-teal-800 px-4 pb-3 pt-5 text-white dark:bg-zinc-800">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-white/15">
                <ShieldCheck size={18} weight="fill" />
              </span>
              <div className="min-w-0 leading-tight">
                <div className="truncate text-sm font-semibold">AushadhiNet</div>
                <div className="text-xs text-white/75">{t("sim_online")}</div>
              </div>
              <WhatsappLogo size={20} weight="fill" className="ml-auto text-white/80" />
            </div>

            <div
              ref={scroller}
              className="h-[460px] space-y-2 overflow-y-auto px-3 py-4 [background-image:radial-gradient(rgb(0_0_0/0.05)_1px,transparent_1px)] [background-size:14px_14px] dark:[background-image:radial-gradient(rgb(255_255_255/0.04)_1px,transparent_1px)]"
              data-testid="sim-messages"
              aria-live="polite"
            >
              {thread.length === 0 && (
                <p className="mx-auto mt-24 w-fit rounded-lg bg-white/80 px-3 py-1.5 text-center text-xs text-zinc-600 shadow-sm dark:bg-zinc-800 dark:text-zinc-300">
                  {t("sim_empty")}
                </p>
              )}
              <AnimatePresence initial={false}>
                {thread.map((m) =>
                  m.buttons.length ? (
                    <motion.div key={m.key} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                      <ConfirmCard
                        card={{ record_id: m.key, text: m.text, buttons: m.buttons }}
                        onRespond={(_, index) => (index === 0 ? send(t("sim_example_yes")) : inputRef.current?.focus())}
                      />
                    </motion.div>
                  ) : (
                    <motion.div
                      key={m.key}
                      initial={{ opacity: 0, y: 6, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{ duration: 0.25 }}
                      className={`flex ${m.mine ? "justify-end" : "justify-start"}`}
                    >
                      <span
                        className={`max-w-[82%] whitespace-pre-line rounded-lg px-2.5 py-1.5 text-[13.5px] leading-snug text-zinc-900 shadow-sm dark:text-zinc-100 ${
                          m.mine ? "rounded-tr-none bg-[#d9fdd3] dark:bg-teal-900" : "rounded-tl-none bg-white dark:bg-zinc-800"
                        }`}
                      >
                        {m.text === "[voice note]" ? (
                          <span className="flex items-center gap-1.5"><Microphone size={14} weight="fill" /> {t("sim_voice_note")}</span>
                        ) : (
                          m.text
                        )}
                        {m.mine && <Checks size={14} className="ml-1.5 inline text-sky-600 dark:text-sky-400" />}
                      </span>
                    </motion.div>
                  ),
                )}
              </AnimatePresence>
            </div>

            <form
              className="flex items-center gap-2 bg-[#f0f2f5] px-2.5 py-2.5 dark:bg-zinc-800"
              onSubmit={(e) => {
                e.preventDefault();
                send(body, true);
              }}
            >
              <label htmlFor="sim-input" className="sr-only">{t("sim_placeholder")}</label>
              <input
                id="sim-input"
                name="message"
                autoComplete="off"
                ref={inputRef}
                className="flex-1 rounded-full border-0 bg-white px-4 py-2 text-sm text-zinc-900 placeholder:text-zinc-500 dark:bg-zinc-700 dark:text-zinc-100 dark:placeholder:text-zinc-400"
                placeholder={t("sim_placeholder")}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                data-testid="sim-input"
              />
              <button
                type="submit"
                className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-teal-700 text-white transition active:scale-95 disabled:opacity-50 dark:bg-teal-500 dark:text-zinc-950"
                disabled={sending || !phone}
                aria-label={t("sim_send")}
                data-testid="sim-send"
              >
                <PaperPlaneRight size={18} weight="fill" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
