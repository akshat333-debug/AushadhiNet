"use client";
/**
 * One facility: latest stock per drug, next-week demand forecast and
 * stock-out probability (backend/api/officer.py's facility_detail).
 */
import { use, useEffect, useState } from "react";
import { api, FacilityDetail } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

export default function FacilityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, ready } = useAuth();
  const [detail, setDetail] = useState<FacilityDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) api.facilityDetail(id).then(setDetail).catch((e) => setError((e as Error).message));
  }, [id, user]);

  if (!ready) return null;
  if (!user) return <p className="text-sm text-gray-500">Sign in as an officer (top right) to view facility {id}.</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!detail) return <p className="text-sm text-gray-500">Loading facility {id}…</p>;

  const latest = new Map<string, FacilityDetail["stock"][number]>();
  for (const s of detail.stock) {
    const prev = latest.get(s.drug_id);
    if (!prev || s.as_of_date >= prev.as_of_date) latest.set(s.drug_id, s);
  }
  const forecast = new Map(detail.forecasts.map((f) => [f.drug_id, f]));
  const f = detail.facility;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold">{f.name}</h1>
      <p className="mb-4 text-sm text-gray-500">
        {f.facility_id} · {f.facility_type} · {f.block ?? "—"} · {f.district_id}
      </p>
      <table className="w-full border-collapse text-sm" data-testid="facility-stock">
        <thead>
          <tr className="border-b text-left">
            <th className="py-1">Drug</th>
            <th className="py-1">On hand</th>
            <th className="py-1">As of</th>
            <th className="py-1">Next-week demand (p10–p90)</th>
            <th className="py-1">Stock-out risk</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(latest.values()).map((s) => {
            const fc = forecast.get(s.drug_id);
            const risk = fc?.stockout_prob ?? 0;
            return (
              <tr key={s.drug_id} className="border-b">
                <td className="py-1">{s.drug_id}</td>
                <td className="py-1">
                  {s.on_hand}
                  {s.status !== "confirmed" && <span className="ml-1 text-xs text-yellow-700">({s.status})</span>}
                </td>
                <td className="py-1">{s.as_of_date}</td>
                <td className="py-1">{fc ? `${fc.p50.toFixed(0)} (${fc.p10.toFixed(0)}–${fc.p90.toFixed(0)})` : "—"}</td>
                <td className={`py-1 ${risk >= 0.5 ? "font-medium text-red-700" : ""}`}>{fc ? `${Math.round(risk * 100)}%` : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
