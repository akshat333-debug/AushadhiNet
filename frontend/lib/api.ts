/**
 * Thin fetch wrapper for the FastAPI backend (modular-plan.md step 40).
 * Every officer-facing call attaches the bearer token from lib/auth.ts;
 * public endpoints (backend/api/public.py) don't need one.
 */
import { getToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
  const contentType = response.headers.get("content-type") || "";
  return (contentType.includes("application/json") ? response.json() : response.text()) as Promise<T>;
}

export interface TransferOrder {
  order_id: string;
  kind: string;
  from_facility_id: string;
  to_facility_id: string;
  drug_id: string | null;
  quantity: number | null;
  status: string;
  drive_minutes: number;
  rationale: string;
  signature: string | null;
}

export interface DistrictSummaryRow {
  district_id: string;
  facilities_reporting: number;
  facilities_at_risk: number;
}

export const api = {
  listOrders: (districtId: string) => request<TransferOrder[]>(`/officer/orders/${districtId}`),
  approveOrder: (orderId: string, districtId: string) =>
    request<TransferOrder>(`/officer/orders/${orderId}/approve?district_id=${encodeURIComponent(districtId)}`, { method: "POST" }),
  rejectOrder: (orderId: string, districtId: string) =>
    request<TransferOrder>(`/officer/orders/${orderId}/reject?district_id=${encodeURIComponent(districtId)}`, { method: "POST" }),
  districtSummary: () => request<DistrictSummaryRow[]>("/public/district-summary"),
  simulatorSend: (payload: { from_phone: string; body?: string; media_base64?: string; media_content_type?: string; message_id: string }) =>
    request<{ status: string }>("/simulator/message", { method: "POST", body: JSON.stringify(payload) }),
  askAgent: (question: string) => request<{ text: string; cited_ids: string[]; draft_order_id: string | null }>("/agent/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  }),
};
