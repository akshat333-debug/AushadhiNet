"use client";
/**
 * Order queue (AC7/AC8's human gate). "Propose transfers" runs the solver
 * and saves drafts; approving calls backend/api/officer.py, the only path
 * that can move an order past `draft`, which also sends the WhatsApp and
 * voice alerts to both facilities. Drafts arrive most urgent first (the
 * destination's days of cover), so "approve the most urgent" takes the top few.
 */
import { useCallback, useEffect, useState } from "react";
import { Checks, ClockCounterClockwise, Lightning, Truck } from "@phosphor-icons/react";
import OrderCard from "@/components/OrderCard";
import { Empty, Notice, PageHeader, Skeleton } from "@/components/ui";
import { api, TransferOrder } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useI18n } from "@/lib/i18n";

const PILOT_DISTRICT = "mh/nashik";
const PAGE = 12;
const TOP = 5;
// "All" shows decisions first (what just happened), then open drafts; the API leaves out expired ones.
const STATUS_ORDER: Record<string, number> = { approved: 0, rejected: 1, dispatched: 2, received: 3, draft: 4 };

export default function OrdersPage() {
  const { user, ready } = useAuth();
  const { t, num, place } = useI18n();
  const [orders, setOrders] = useState<TransferOrder[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<"draft" | "all">("draft");
  const [limit, setLimit] = useState(PAGE);
  // Bulk approval sends WhatsApp orders, so it takes a second click within a few seconds.
  const [confirmTop, setConfirmTop] = useState(false);
  useEffect(() => {
    if (!confirmTop) return;
    const timer = setTimeout(() => setConfirmTop(false), 4000);
    return () => clearTimeout(timer);
  }, [confirmTop]);

  const districtId = user && user.jurisdiction.includes("/") ? user.jurisdiction : PILOT_DISTRICT;

  const refresh = useCallback(async () => {
    try {
      setOrders(await api.listOrders(districtId));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [districtId]);

  useEffect(() => {
    if (!user) return;
    refresh();
  }, [user, refresh]);

  // The notice is shown only after the list refresh, so it never sits over stale orders.
  async function act(fn: () => Promise<string | void>) {
    setBusy(true);
    setNotice(null);
    try {
      const message = await fn();
      await refresh();
      if (message) {
        setNotice(message);
        setLimit(PAGE);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return null;
  if (!user) {
    return (
      <div className="mx-auto max-w-xl pt-8">
        <Empty icon={<Truck size={22} />} title={t("orders_title")} hint={t("orders_signin")} />
      </div>
    );
  }

  const matching = (orders ?? [])
    .filter((o) => filter === "all" || o.status === "draft")
    .sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));
  const shown = matching.slice(0, limit);
  const draftOrders = (orders ?? []).filter((o) => o.status === "draft");
  const units = draftOrders.reduce((a, o) => a + (o.quantity ?? 0), 0);
  const facilities = new Set(draftOrders.flatMap((o) => [o.from_facility_id, o.to_facility_id])).size;
  const top = draftOrders.slice(0, TOP);

  function approveTop() {
    if (!confirmTop) return setConfirmTop(true);
    setConfirmTop(false);
    act(async () => {
      // Independent orders, each signed and alerted on its own: in parallel, not one after another.
      await Promise.all(top.map((o) => api.approveOrder(o.order_id)));
      return t("notice_approved_n", { n: num(top.length) });
    });
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title={`${t("orders_title")}, ${place(districtId)}`}
        sub={t("orders_sub")}
        actions={
          <>
            {user.role === "state" && (
              <button
                className="btn-secondary"
                disabled={busy}
                onClick={() => act(async () => t("notice_escalated", { n: num((await api.runEscalation()).length) }))}
              >
                <ClockCounterClockwise size={16} /> {t("escalate")}
              </button>
            )}
            {top.length > 1 && (
              <button className={confirmTop ? "btn-primary" : "btn-secondary"} disabled={busy} onClick={approveTop} data-testid="bulk-approve">
                <Checks size={16} weight="bold" /> {confirmTop ? t("confirm_approve_top", { n: num(top.length) }) : t("approve_top", { n: num(top.length) })}
              </button>
            )}
            <button
              className={top.length > 1 ? "btn-secondary" : "btn-primary"}
              disabled={busy}
              data-testid="propose"
              onClick={() => act(async () => t("notice_proposed", { n: num((await api.proposeOrders(districtId)).length) }))}
            >
              <Lightning size={16} weight="fill" /> {busy ? t("working") : t("propose")}
            </button>
          </>
        }
      />

      {notice && <Notice testId="notice">{notice}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}

      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="muted text-sm">
          {orders ? t("orders_summary", { drafts: num(draftOrders.length), units: num(units), facilities: num(facilities) }) : ""}
        </p>
        <label className="flex items-center gap-2 text-sm">
          <span className="label">{t("filter_label")}</span>
          <select className="field w-auto py-1.5" value={filter} onChange={(e) => { setFilter(e.target.value as "draft" | "all"); setLimit(PAGE); }}>
            <option value="draft">{t("filter_drafts")}</option>
            <option value="all">{t("filter_all")}</option>
          </select>
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-2" data-testid="order-list">
        {!orders && Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-44 rounded-xl" />)}
        {shown.map((order) => (
            <OrderCard
              key={order.order_id}
              order={order}
              busy={busy}
              onApprove={(id) => act(async () => void (await api.approveOrder(id)))}
              onReject={(id) => act(async () => void (await api.rejectOrder(id)))}
            />
          ))}
      </div>
      {matching.length > shown.length && (
        <div className="mt-4 flex justify-center">
          <button className="btn-secondary" onClick={() => setLimit((n) => n + PAGE)}>
            {t("orders_show_more", { n: num(Math.min(PAGE, matching.length - shown.length)) })}
          </button>
        </div>
      )}
      {orders && shown.length === 0 && !error && (
        <Empty
          icon={<Truck size={22} />}
          title={filter === "draft" ? t("orders_empty_drafts") : t("orders_empty_all")}
          hint={t("orders_empty_hint")}
        />
      )}
    </div>
  );
}
