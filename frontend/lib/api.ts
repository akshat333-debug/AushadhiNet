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
    let message = body || response.statusText;
    try {
      const detail = JSON.parse(body).detail;
      if (typeof detail === "string") message = detail;
    } catch {
      /* not JSON: keep the raw text */
    }
    throw new ApiError(response.status, message);
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
  // added by the orders list endpoint for triage
  from_name?: string | null;
  to_name?: string | null;
  dest_cover_days?: number | null;
  dest_on_hand?: number | null;
  dest_cover_after_days?: number | null; // counting every draft to this destination
  src_on_hand_after?: number | null;
  report_age_days?: number | null;
  district_gap?: boolean;
}

export interface DistrictSummaryRow {
  district_id: string;
  facilities_reporting: number;
  facilities_at_risk: number;
  at_risk_by_drug: Record<string, number>;
  escalate: Record<string, number>; // drug -> district weeks of cover, below the solver's 2-week plan
  procurement_units: Record<string, number>; // drug -> units to request from the state
  facilities_needing_transfer: number;
}

export interface CoverageRow {
  state: string;
  code: string;
  districts: number;
  facilities: number;
  by_type: Record<string, number>;
  live_districts: number;
}

export interface Contact {
  facility_id: string;
  name: string;
  phone: string;
  lat: number;
  lon: number;
}

interface Route {
  from_id: string;
  from_name: string;
  to_id: string;
  to_name: string;
  minutes: number;
  order_id?: string | null; // set once an officer approved this suggestion today
}

/** Today's beds and staff for one district, with referral and deputation suggestions (backend/capacity.py). */
export interface Capacity {
  date: string;
  demo_baseline: boolean;
  beds: {
    facilities: number;
    occupied: number;
    total: number;
    full: { facility_id: string; name: string; occupied: number; total: number }[];
    full_count: number;
    referrals: (Route & { patients: number })[];
  };
  staff: {
    rostered: number;
    present: number;
    facilities: number;
    nobody: { facility_id: string; name: string }[];
    nobody_count: number;
    off_site: { facility_id: string; name: string; role: string; distance_m: number }[];
    deputations: (Route & { role: string; staff: number })[];
  };
}

export interface OutboxMessage {
  seq: number;
  kind: string;
  body: string;
  buttons: string[];
}

export interface FacilitySummary {
  facility_id: string;
  name: string;
  block: string | null;
  type: string;
  lat: number;
  lon: number;
  at_risk: boolean;
  short_count: number;
  short_drugs: string[];
}

export interface StockRow {
  drug_id: string;
  on_hand: number;
  as_of_date: string;
  reported_at: string;
  status: string;
  reporter_phone_hash: string;
}

export interface ForecastRow {
  drug_id: string;
  p10: number;
  p50: number;
  p90: number;
  stockout_prob: number;
  horizon: number;
  origin_date: string;
}

export interface FacilityDetail {
  facility: { facility_id: string; name: string; district_id: string; block: string | null; facility_type: string };
  stock: StockRow[];
  forecasts: ForecastRow[];
}

export const api = {
  listOrders: (districtId: string) => request<TransferOrder[]>(`/officer/orders/${districtId}`),
  approveOrder: (orderId: string) => request<TransferOrder>(`/officer/orders/${orderId}/approve`, { method: "POST" }),
  receiveOrder: (orderId: string) => request<TransferOrder>(`/officer/orders/${orderId}/received`, { method: "POST" }),
  rejectOrder: (orderId: string) => request<TransferOrder>(`/officer/orders/${orderId}/reject`, { method: "POST" }),
  proposeOrders: (districtId: string) => request<TransferOrder[]>(`/officer/propose/${districtId}`, { method: "POST" }),
  runEscalation: () => request<TransferOrder[]>("/officer/escalation/sweep", { method: "POST" }),
  approveCapacity: (kind: "referral" | "deputation", fromId: string, toId: string) =>
    request<TransferOrder>("/officer/capacity/approve", { method: "POST", body: JSON.stringify({ kind, from_id: fromId, to_id: toId }) }),
  capacity: (districtId: string) => request<Capacity>(`/officer/capacity/${districtId}`),
  districtFacilities: (districtId: string) => request<FacilitySummary[]>(`/officer/districts/${districtId}/facilities`),
  facilityDetail: (facilityId: string) => request<FacilityDetail>(`/officer/facility/${encodeURIComponent(facilityId)}`),
  simulatorContacts: () => request<Contact[]>("/simulator/contacts"),
  drugNames: () => request<Record<string, Record<string, string>>>("/public/drug-names"),
  facilityPoints: (districtId: string) => request<[number, number][]>(`/public/facility-points?district_id=${encodeURIComponent(districtId)}`),
  simulatorOutbox: (phone: string) => request<OutboxMessage[]>(`/simulator/outbox?phone=${encodeURIComponent(phone)}`),
  districtSummary: () => request<DistrictSummaryRow[]>("/public/district-summary"),
  coverage: () => request<CoverageRow[]>("/public/coverage"),
  simulatorSend: (payload: { from_phone: string; body?: string; media_base64?: string; media_content_type?: string; message_id: string; lang?: string; latitude?: number; longitude?: number }) =>
    request<{ status: string }>("/simulator/message", { method: "POST", body: JSON.stringify(payload) }),
  askAgent: (question: string, lang = "en") => request<{ text: string; cited_ids: string[]; draft_order_id: string | null }>("/agent/ask", {
    method: "POST",
    body: JSON.stringify({ question, lang }),
  }),
};
