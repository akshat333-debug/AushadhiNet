"use client";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowClockwise, ArrowRight, Check, Info, SealCheck, Truck, X } from "@phosphor-icons/react";
import { TransferOrder } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900",
  approved: "bg-teal-50 text-teal-800 ring-teal-200 dark:bg-teal-950/60 dark:text-teal-300 dark:ring-teal-900",
  dispatched: "bg-indigo-50 text-indigo-800 ring-indigo-200 dark:bg-indigo-950/50 dark:text-indigo-300 dark:ring-indigo-900",
  received: "bg-sky-50 text-sky-800 ring-sky-200 dark:bg-sky-950/50 dark:text-sky-300 dark:ring-sky-900",
  rejected: "bg-zinc-100 text-zinc-600 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:ring-zinc-700",
  expired: "bg-zinc-100 text-zinc-500 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-500 dark:ring-zinc-700",
};

export default function OrderCard({
  order,
  busy,
  onApprove,
  onReject,
  onReceive,
  onDispatch,
}: {
  order: TransferOrder;
  busy?: boolean;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onReceive?: (id: string) => void;
  onDispatch?: (id: string) => void;
}) {
  const { t, num, drug, date } = useI18n();
  const qty = (n: number) => (order.unit ? `${num(n)} × ${order.unit}` : t("order_units", { n: num(n) }));
  // Rejecting can't be undone, so it takes a second click within a few seconds.
  const [confirming, setConfirming] = useState(false);
  useEffect(() => {
    if (!confirming) return;
    const timer = setTimeout(() => setConfirming(false), 4000);
    return () => clearTimeout(timer);
  }, [confirming]);
  const label = (id: string) => (id === order.from_facility_id ? order.from_name : order.to_name);
  const days = order.dest_cover_days;
  const urgency = order.status !== "draft" || days == null ? null : days < 1
    ? { text: order.dest_on_hand === 0 ? t("order_out_now") : t("order_under_day"), style: "bg-rose-600 text-white dark:bg-rose-500 dark:text-zinc-950" }
    : { text: t("order_runs_out", { n: num(days) }), style: days < 4 ? "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:ring-rose-900" : "bg-zinc-100 text-zinc-700 ring-1 ring-inset ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700" };
  const place = (id: string) => (
    <a href={`/facility/${id}`} className="group min-w-0">
      <span className="block truncate font-medium group-hover:text-teal-700 dark:group-hover:text-teal-400">{label(id) ?? id}</span>
      <span className="muted block font-mono text-xs" translate="no">{id}</span>
    </a>
  );

  return (
    <motion.div
      // Enter animation only: an exit animation keeps a stale card (and its Approve
      // button) in the page after its order has changed, where it can still be clicked.
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-4"
      data-testid={`order-card-${order.order_id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">
            <Truck size={20} weight="duotone" />
          </span>
          <div>
            <div className="font-semibold">{order.drug_id ? drug(order.drug_id) : order.kind}</div>
            {order.quantity != null && <div className="muted text-sm">{qty(order.quantity)}</div>}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${STATUS_STYLE[order.status] ?? STATUS_STYLE.expired}`}
            data-testid={`order-status-${order.order_id}`}
          >
            {t(`status_${order.status}` as MessageKey)}
          </span>
          {urgency && <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${urgency.style}`} data-testid="order-urgency">{urgency.text}</span>}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-sm">
        {place(order.from_facility_id)}
        <ArrowRight size={16} className="text-zinc-400" />
        {place(order.to_facility_id)}
      </div>

      {order.status === "draft" && (order.dest_cover_after_days != null || order.report_date) && (
        <p className="muted mt-3 text-xs leading-relaxed" data-testid="order-after">
          {order.dest_cover_after_days != null && order.src_on_hand_after != null &&
            t("order_after", { dst: num(order.dest_cover_after_days, 1), src: qty(order.src_on_hand_after) })}
          {order.scenario_stock && order.report_date ? (
            <span className="ml-1">· {t("order_scenario_date", { date: date(order.report_date) })}</span>
          ) : (order.report_age_days ?? 0) >= 1 && (
            <span className="ml-1 text-amber-700 dark:text-amber-400">· {t("order_report_age", { n: num(order.report_age_days!) })}</span>
          )}
        </p>
      )}

      {order.status === "approved" && !order.alerted_at && (
        <p className="mt-3 flex gap-1.5 rounded-lg bg-rose-50 px-2.5 py-1.5 text-xs text-rose-900 dark:bg-rose-950/40 dark:text-rose-200" data-testid="alerts-pending">
          <Info size={14} className="mt-px shrink-0" /> {t("alerts_pending")}
        </p>
      )}

      {order.district_gap && order.status === "draft" && (
        <p className="mt-3 flex gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          <Info size={14} className="mt-px shrink-0" /> {t("order_gap_note")}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <span className="muted flex items-center gap-3 text-xs">
          <span>{order.drive_minutes < 1 ? t("colocated") : t("min_drive", { n: num(order.drive_minutes) })}</span>
          {order.signature && (
            <span className="flex items-center gap-1 text-teal-700 dark:text-teal-400">
              <SealCheck size={14} weight="fill" /> {t("order_signed")}
            </span>
          )}
        </span>
        {order.status === "approved" && !order.alerted_at && order.can_approve !== false && (
          <button className="btn-primary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onApprove(order.order_id)} data-testid={`resend-${order.order_id}`}>
            <ArrowClockwise size={14} weight="bold" /> {t("resend_alerts")}
          </button>
        )}
        {order.status === "approved" && order.kind === "drug_transfer" && onDispatch && (
          <button className="btn-secondary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onDispatch(order.order_id)} data-testid={`dispatch-${order.order_id}`}>
            <Truck size={14} /> {t("mark_dispatched")}
          </button>
        )}
        {(order.status === "approved" || order.status === "dispatched") && onReceive && (
          <button className="btn-secondary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onReceive(order.order_id)} data-testid={`receive-${order.order_id}`}>
            <Check size={14} weight="bold" /> {t("mark_received")}
          </button>
        )}
        {order.status === "draft" && order.can_approve === false && (
          <span className="muted text-xs" data-testid="needs-state-officer">{t("needs_state_officer")}</span>
        )}
        {order.status === "draft" && order.can_approve !== false && (
          <div className="flex gap-2">
            <button
              className={`${confirming ? "bg-rose-600 text-white hover:bg-rose-700 dark:bg-rose-500 dark:text-zinc-950" : ""} btn-danger px-3 py-1.5 text-xs`}
              disabled={busy}
              onClick={() => (confirming ? onReject(order.order_id) : setConfirming(true))}
              data-testid={`reject-${order.order_id}`}
            >
              <X size={14} /> {confirming ? t("confirm_reject") : t("reject")}
            </button>
            <button className="btn-primary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onApprove(order.order_id)} data-testid={`approve-${order.order_id}`}>
              <Check size={14} weight="bold" /> {t("approve")}
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
