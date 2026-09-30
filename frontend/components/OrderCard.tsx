"use client";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, Check, SealCheck, Truck, X } from "@phosphor-icons/react";
import { TransferOrder } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900",
  approved: "bg-teal-50 text-teal-800 ring-teal-200 dark:bg-teal-950/60 dark:text-teal-300 dark:ring-teal-900",
  rejected: "bg-zinc-100 text-zinc-600 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:ring-zinc-700",
  expired: "bg-zinc-100 text-zinc-500 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-500 dark:ring-zinc-700",
};

export default function OrderCard({
  order,
  names,
  busy,
  onApprove,
  onReject,
}: {
  order: TransferOrder;
  names: Record<string, string>;
  busy?: boolean;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const { t, num, drug } = useI18n();
  // Rejecting can't be undone, so it takes a second click within a few seconds.
  const [confirming, setConfirming] = useState(false);
  useEffect(() => {
    if (!confirming) return;
    const timer = setTimeout(() => setConfirming(false), 4000);
    return () => clearTimeout(timer);
  }, [confirming]);
  const place = (id: string) => (
    <a href={`/facility/${id}`} className="group min-w-0">
      <span className="block truncate font-medium group-hover:text-teal-700 dark:group-hover:text-teal-400">{names[id] ?? id}</span>
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
            {order.quantity != null && <div className="muted text-sm">{num(order.quantity)}</div>}
          </div>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${STATUS_STYLE[order.status] ?? STATUS_STYLE.expired}`}
          data-testid={`order-status-${order.order_id}`}
        >
          {t(`status_${order.status}` as MessageKey)}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-sm">
        {place(order.from_facility_id)}
        <ArrowRight size={16} className="text-zinc-400" />
        {place(order.to_facility_id)}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <span className="muted flex items-center gap-3 text-xs">
          <span>{order.drive_minutes < 1 ? t("colocated") : t("min_drive", { n: num(order.drive_minutes) })}</span>
          {order.signature && (
            <span className="flex items-center gap-1 text-teal-700 dark:text-teal-400">
              <SealCheck size={14} weight="fill" /> {t("order_signed")}
            </span>
          )}
        </span>
        {order.status === "draft" && (
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
