"use client";
/**
 * Order queue (AC7/AC8's human gate). "Propose transfers" runs the solver
 * and saves drafts; approving calls backend/api/officer.py, the only path
 * that can move an order past `draft`, which also sends the WhatsApp and
 * voice alerts to both facilities.
 */
import { useCallback, useEffect, useState } from "react";
import OrderCard from "@/components/OrderCard";
import { api, TransferOrder } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

const PILOT_DISTRICT = "mh/nashik";

export default function OrdersPage() {
  const { user, ready } = useAuth();
  const [orders, setOrders] = useState<TransferOrder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<"draft" | "all">("draft");

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
    if (user) refresh();
  }, [user, refresh]);

  // The notice is shown only after the list refresh, so it never sits over stale orders.
  async function act(label: string, fn: () => Promise<string | void>) {
    setBusy(true);
    setNotice(null);
    try {
      const message = await fn();
      await refresh();
      if (message) setNotice(message);
    } catch (err) {
      setError(`${label}: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return null;
  if (!user) {
    return <p className="text-sm text-gray-500">Sign in as a block, district or state officer (top right) to view orders.</p>;
  }

  const shown = filter === "draft" ? orders.filter((o) => o.status === "draft") : orders;

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-4 text-xl font-semibold">Transfer Orders — {districtId}</h1>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          disabled={busy}
          data-testid="propose"
          onClick={() =>
            act("Propose", async () => {
              const drafts = await api.proposeOrders(districtId);
              return `${drafts.length} draft transfer(s) proposed.`;
            })
          }
        >
          {busy ? "Working…" : "Propose transfers"}
        </button>
        {user.role === "state" && (
          <button
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
            disabled={busy}
            onClick={() =>
              act("Escalation", async () => {
                const escalated = await api.runEscalation();
                return `${escalated.length} overdue order(s) escalated.`;
              })
            }
          >
            Run escalation check
          </button>
        )}
        <select className="ml-auto rounded border px-1 py-0.5 text-sm" value={filter} onChange={(e) => setFilter(e.target.value as "draft" | "all")}>
          <option value="draft">Drafts</option>
          <option value="all">All</option>
        </select>
      </div>
      {notice && <p className="mb-2 text-sm text-green-700" data-testid="notice">{notice}</p>}
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
      <div className="space-y-3" data-testid="order-list">
        {shown.map((order) => (
          <OrderCard
            key={order.order_id}
            order={order}
            onApprove={(id) => act("Approve", async () => void (await api.approveOrder(id)))}
            onReject={(id) => act("Reject", async () => void (await api.rejectOrder(id)))}
          />
        ))}
        {shown.length === 0 && !error && <p className="text-sm text-gray-500">No {filter === "draft" ? "draft " : ""}orders yet.</p>}
      </div>
    </div>
  );
}
