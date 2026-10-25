"use client";
/**
 * The three-step story for first-time visitors (and judges): WhatsApp report,
 * Gemini read with a confirmation, transfer on the map. One 6 s loop played in
 * sequence across the three panels; with reduced motion it shows the end state.
 */
import { motion, useReducedMotion } from "motion/react";
import { ChatCircleText, MapTrifold, Sparkle } from "@phosphor-icons/react";
import { useI18n } from "@/lib/i18n";

const CYCLE = 6;

// Keyframes on the shared cycle: hidden until `at` (fraction of the cycle), shown until the end.
function useStep(at: number) {
  const reduce = useReducedMotion();
  if (reduce) return { initial: false as const, animate: { opacity: 1 } };
  return {
    initial: { opacity: 0 },
    animate: { opacity: [0, 0, 1, 1, 0] },
    transition: { duration: CYCLE, times: [0, at, at + 0.05, 0.93, 1], repeat: Infinity, ease: "easeOut" as const },
  };
}

function Phone() {
  const a = useStep(0.02), b = useStep(0.12), c = useStep(0.22);
  return (
    <svg viewBox="0 0 200 120" className="h-full w-full" aria-hidden>
      <rect x="62" y="6" width="76" height="108" rx="12" className="fill-zinc-100 stroke-zinc-300 dark:fill-zinc-800 dark:stroke-zinc-700" strokeWidth="1.5" />
      <rect x="68" y="16" width="64" height="10" rx="3" className="fill-teal-700/15 dark:fill-teal-400/20" />
      <motion.g {...a}>
        <rect x="88" y="34" width="44" height="16" rx="6" className="fill-teal-600 dark:fill-teal-500" />
        <text x="110" y="45.5" textAnchor="middle" className="fill-white text-[8px] font-semibold dark:fill-zinc-950">ORS 45</text>
      </motion.g>
      <motion.g {...b}>
        <rect x="80" y="56" width="52" height="16" rx="6" className="fill-teal-600 dark:fill-teal-500" />
        <text x="106" y="67.5" textAnchor="middle" className="fill-white text-[8px] font-semibold dark:fill-zinc-950">Zinc 120</text>
      </motion.g>
      <motion.g {...c}>
        <rect x="96" y="78" width="36" height="26" rx="6" className="fill-teal-600 dark:fill-teal-500" />
        <path d="M102 99 l7-9 5 6 4-4 8 7z" className="fill-white/85 dark:fill-zinc-950/80" />
        <circle cx="122" cy="85" r="2.5" className="fill-white/85 dark:fill-zinc-950/80" />
      </motion.g>
    </svg>
  );
}

function Read() {
  const reduce = useReducedMotion();
  const card = useStep(0.36), yes = useStep(0.46);
  return (
    <svg viewBox="0 0 200 120" className="h-full w-full" aria-hidden>
      <rect x="20" y="14" width="70" height="92" rx="6" className="fill-amber-50 stroke-amber-200 dark:fill-amber-950/40 dark:stroke-amber-900" strokeWidth="1.5" />
      {[34, 52, 70, 88].map((y) => (
        <path key={y} d={`M30 ${y} q8 -4 16 0 t16 0 t16 0`} className="stroke-zinc-500 dark:stroke-zinc-400" strokeWidth="1.5" fill="none" />
      ))}
      {!reduce && (
        <motion.rect
          x="22" width="66" height="3" rx="1.5" className="fill-teal-500/70"
          animate={{ y: [18, 18, 100, 100], opacity: [0, 1, 1, 0] }}
          transition={{ duration: CYCLE, times: [0, 0.26, 0.36, 0.37], repeat: Infinity }}
        />
      )}
      <motion.g {...card}>
        <rect x="104" y="22" width="80" height="56" rx="8" className="fill-white stroke-zinc-200 dark:fill-zinc-900 dark:stroke-zinc-700" strokeWidth="1.5" />
        <text x="114" y="40" className="fill-zinc-800 text-[8px] font-semibold dark:fill-zinc-100">ORS · 45</text>
        <text x="114" y="54" className="fill-zinc-800 text-[8px] font-semibold dark:fill-zinc-100">Zinc · 120</text>
        <text x="114" y="68" className="fill-zinc-500 text-[7px] dark:fill-zinc-400">Confirm?</text>
      </motion.g>
      <motion.g {...yes}>
        <rect x="140" y="86" width="44" height="18" rx="9" className="fill-teal-600 dark:fill-teal-500" />
        <text x="162" y="98" textAnchor="middle" className="fill-white text-[8px] font-semibold dark:fill-zinc-950">YES</text>
      </motion.g>
    </svg>
  );
}

function Move() {
  const reduce = useReducedMotion();
  const dots: [number, number][] = [[40, 30], [70, 84], [112, 46], [150, 96], [172, 30], [96, 100]];
  return (
    <svg viewBox="0 0 200 120" className="h-full w-full" aria-hidden>
      {dots.map(([x, y]) => <circle key={`${x}${y}`} cx={x} cy={y} r="4" className="fill-teal-700/40 dark:fill-teal-300/40" />)}
      <circle cx="56" cy="58" r="6" className="fill-teal-700 dark:fill-teal-300" />
      <motion.path
        d="M56 58 Q100 18 146 62" fill="none" strokeWidth="2" strokeDasharray="4 4"
        className="stroke-teal-700 dark:stroke-teal-300"
        initial={reduce ? false : { pathLength: 0 }}
        animate={reduce ? { pathLength: 1 } : { pathLength: [0, 0, 1, 1, 0] }}
        transition={{ duration: CYCLE, times: [0, 0.58, 0.74, 0.93, 1], repeat: Infinity }}
      />
      <motion.circle
        cx="146" cy="62" r="7"
        initial={false}
        animate={reduce ? { fill: "#0f766e" } : { fill: ["#e11d48", "#e11d48", "#0f766e", "#0f766e", "#e11d48"], scale: [1, 1, 1.25, 1, 1] }}
        transition={{ duration: CYCLE, times: [0, 0.74, 0.8, 0.93, 1], repeat: Infinity }}
        style={{ transformOrigin: "146px 62px" }}
      />
    </svg>
  );
}

export default function HowItWorks() {
  const { t } = useI18n();
  const steps = [
    { icon: <ChatCircleText size={16} weight="duotone" />, text: t("how_1"), art: <Phone /> },
    { icon: <Sparkle size={16} weight="duotone" />, text: t("how_2"), art: <Read /> },
    { icon: <MapTrifold size={16} weight="duotone" />, text: t("how_3"), art: <Move /> },
  ];
  return (
    <section className="card p-5" aria-labelledby="how-title">
      <h2 id="how-title" className="h2 mb-4">{t("how_title")}</h2>
      <ol className="grid gap-4 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={i} className="flex flex-col gap-3">
            <div className="h-32 rounded-lg bg-zinc-50 dark:bg-zinc-950/60">{s.art}</div>
            <p className="flex gap-2 text-sm leading-relaxed">
              <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">{s.icon}</span>
              <span><span className="font-medium">{i + 1}. </span>{s.text}</span>
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
