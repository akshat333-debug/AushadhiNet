"use client";
/**
 * National -> state -> district -> facility drill-down dashboard. State
 * and district tiles come from the public district summary; facility
 * tiles load from the officer API once signed in.
 */
import { useEffect, useState } from "react";
import MapView, { DrillLevel } from "@/components/MapView";
import AlertList, { Alert } from "@/components/AlertList";
import { api, DistrictSummaryRow } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

const STATE_NAMES: Record<string, string> = { mh: "Maharashtra", hr: "Haryana", as: "Assam", ml: "Meghalaya" };

export default function DashboardPage() {
  const [summary, setSummary] = useState<DistrictSummaryRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    api.districtSummary().then(setSummary).catch((e) => setError((e as Error).message));
  }, []);

  const states = Array.from(new Set(summary.map((r) => r.district_id.split("/")[0])));
  const root: DrillLevel = {
    id: "national",
    label: "India",
    children: states.map((code) => ({
      id: code,
      label: STATE_NAMES[code] || code.toUpperCase(),
      children: summary
        .filter((r) => r.district_id.startsWith(`${code}/`))
        .map((r) => ({
          id: r.district_id,
          label: `${r.district_id.split("/")[1]} · ${r.facilities_at_risk}/${r.facilities_reporting} facilities at risk`,
          tone: r.facilities_at_risk ? "risk" : "ok",
          load: async () => {
            if (!user) throw new Error("Sign in as an officer (top right) to see facilities.");
            const facilities = await api.districtFacilities(r.district_id);
            return facilities.map((f) => ({
              id: f.facility_id,
              label: `${f.name} (${f.type})`,
              tone: f.at_risk ? "risk" : "ok",
              href: `/facility/${f.facility_id}`,
            }));
          },
        })),
    })),
  };

  const alerts: Alert[] = summary.flatMap((r) =>
    Object.entries(r.at_risk_by_drug).map(([drug, count]) => ({
      id: `${r.district_id}-${drug}`,
      text: `${r.district_id}: ${drug} under 1 week of cover at ${count} of ${r.facilities_reporting} facilities`,
      severity: count / r.facilities_reporting > 0.5 ? "critical" : "warning",
    })),
  );

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">National Dashboard</h1>
      {error && <p className="mb-2 text-sm text-red-600">Could not load summary: {error}</p>}
      <div className="grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2">
          <MapView root={root} />
        </div>
        <div>
          <h2 className="mb-2 font-medium">Alerts</h2>
          <AlertList alerts={alerts} />
          {!alerts.length && !error && <p className="text-sm text-gray-500">No drugs under a week of cover.</p>}
        </div>
      </div>
    </div>
  );
}
