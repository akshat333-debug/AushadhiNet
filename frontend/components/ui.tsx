"use client";
import { motion } from "motion/react";
import { useI18n } from "@/lib/i18n";

export function PageHeader({ title, sub, actions }: { title: string; sub?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        <h1 className="h1">{title}</h1>
        {sub && <p className="muted mt-1.5 text-sm leading-relaxed md:text-base">{sub}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Staggered entrance for page sections: shows the reader what loaded, in order. */
export function Reveal({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function Stat({ label, value, hint, tone = "neutral" }: { label: string; value: React.ReactNode; hint?: string; tone?: "neutral" | "risk" }) {
  return (
    <div className="card p-4 md:p-5">
      <div className="label">{label}</div>
      <div className={`mt-1.5 text-2xl font-semibold tracking-tight md:text-3xl ${tone === "risk" ? "text-rose-700 dark:text-rose-400" : ""}`}>{value}</div>
      {hint && <div className="muted mt-1 text-xs">{hint}</div>}
    </div>
  );
}

export type RiskLevel = "high" | "watch" | "low";

export function riskLevel(prob: number): RiskLevel {
  return prob >= 0.5 ? "high" : prob >= 0.2 ? "watch" : "low";
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const { t } = useI18n();
  const styles = {
    high: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:ring-rose-900",
    watch: "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900",
    low: "bg-zinc-100 text-zinc-700 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700",
  };
  const label = { high: t("risk_high"), watch: t("risk_watch"), low: t("risk_low") };
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles[level]}`}>{label[level]}</span>;
}

export function Empty({ icon, title, hint, action }: { icon: React.ReactNode; title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="card flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-3 grid h-11 w-11 place-items-center rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">{icon}</div>
      <p className="font-medium">{title}</p>
      {hint && <p className="muted mt-1 max-w-sm text-sm">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-zinc-200/70 dark:bg-zinc-800 ${className}`} />;
}

export function Notice({ tone = "info", children, testId }: { tone?: "info" | "error"; children: React.ReactNode; testId?: string }) {
  const styles = tone === "error"
    ? "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300"
    : "border-teal-200 bg-teal-50 text-teal-900 dark:border-teal-900 dark:bg-teal-950/50 dark:text-teal-200";
  return <p className={`mb-4 rounded-lg border px-3 py-2 text-sm ${styles}`} data-testid={testId} role={tone === "error" ? "alert" : "status"}>{children}</p>;
}
