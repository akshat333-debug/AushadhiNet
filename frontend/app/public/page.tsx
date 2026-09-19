"use client";
/**
 * Public transparency view (modular-plan.md step 43, project.md's public
 * role): aggregate district counts only, calling backend/api/public.py --
 * the same endpoint the DoD test proves never returns a facility-level
 * identifier.
 */
import { useEffect, useState } from "react";
import { api, DistrictSummaryRow } from "@/lib/api";

export default function PublicPage() {
  const [rows, setRows] = useState<DistrictSummaryRow[]>([]);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.districtSummary().then(setRows).catch((e) => setError((e as Error).message));
  }, []);

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-4 text-xl font-semibold">Public Transparency View</h1>
      <p className="mb-3 text-sm text-gray-500">Facilities with at least one medicine under one week of cover. No facility is named.</p>
      {error && <p className="mb-2 text-sm text-red-600">Could not load: {error}</p>}
      <table className="w-full border-collapse text-sm" data-testid="public-table">
        <thead>
          <tr className="border-b text-left">
            <th className="py-1">District</th>
            <th className="py-1">Facilities reporting</th>
            <th className="py-1">At risk</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.district_id} className="border-b">
              <td className="py-1">{r.district_id}</td>
              <td className="py-1">{r.facilities_reporting}</td>
              <td className="py-1">{r.facilities_at_risk}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
