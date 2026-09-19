"use client";
import { TransferOrder } from "@/lib/api";

export default function OrderCard({
  order,
  onApprove,
  onReject,
}: {
  order: TransferOrder;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  return (
    <div className="rounded border bg-white p-3" data-testid={`order-card-${order.order_id}`}>
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-gray-500">{order.order_id.slice(0, 8)}</span>
        <span
          className={`rounded px-2 py-0.5 text-xs ${
            order.status === "approved" ? "bg-green-100" : order.status === "rejected" ? "bg-red-100" : "bg-yellow-100"
          }`}
          data-testid={`order-status-${order.order_id}`}
        >
          {order.status}
        </span>
      </div>
      <p className="mt-1 text-sm">
        <a className="underline" href={`/facility/${order.from_facility_id}`}>{order.from_facility_id}</a> &rarr;{" "}
        <a className="underline" href={`/facility/${order.to_facility_id}`}>{order.to_facility_id}</a>
        {order.drug_id && ` (${order.drug_id} x${order.quantity})`}
      </p>
      <p className="text-xs text-gray-500">{order.rationale}</p>
      <p className="text-xs text-gray-400">
        {order.drive_minutes < 1 ? "Same coordinates in the facility directory (co-located)" : `${order.drive_minutes.toFixed(0)} min drive`}
      </p>
      {order.status === "draft" && (
        <div className="mt-2 flex gap-2">
          <button
            className="rounded bg-green-600 px-3 py-1 text-xs text-white"
            onClick={() => onApprove(order.order_id)}
            data-testid={`approve-${order.order_id}`}
          >
            Approve
          </button>
          <button
            className="rounded bg-red-600 px-3 py-1 text-xs text-white"
            onClick={() => onReject(order.order_id)}
            data-testid={`reject-${order.order_id}`}
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
