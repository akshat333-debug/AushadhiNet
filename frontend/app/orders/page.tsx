"use client";
/**
 * Order queue with approve/reject (modular-plan.md step 42, AC7/AC8's
 * human gate). Approving/rejecting calls backend/api/officer.py, which is
 * the only path that can move an order past `draft`.
 */
import { useEffect, useState } from "react";
import OrderCard from "@/components/OrderCard";
import { api, TransferOrder } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

const DISTRICT_ID = "mh/nashik"; // pilot district (project.md)

export default function OrdersPage() {
  const [orders, setOrders] = useState<TransferOrder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { user, ready } = useAuth();

  async function refresh() {
    try {
      const data = await api.listOrders(DISTRICT_ID);
      setOrders(data);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleApprove(id: string) {
    await api.approveOrder(id, DISTRICT_ID);
    await refresh();
  }

  async function handleReject(id: string) {
    await api.rejectOrder(id, DISTRICT_ID);
    await refresh();
  }

  if (!ready) {
    return null; // avoid a hydration mismatch flash before the client auth check runs
  }
  if (!user) {
    return <p className="text-sm text-gray-500">Sign in as a block/district/state officer to view orders.</p>;
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-4 text-xl font-semibold">Transfer Orders — {DISTRICT_ID}</h1>
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
      <div className="space-y-3" data-testid="order-list">
        {orders.map((order) => (
          <OrderCard key={order.order_id} order={order} onApprove={handleApprove} onReject={handleReject} />
        ))}
        {orders.length === 0 && !error && <p className="text-sm text-gray-500">No orders yet.</p>}
      </div>
    </div>
  );
}
