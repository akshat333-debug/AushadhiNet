"use client";
/**
 * National -> state -> district -> facility drill-down dashboard
 * (modular-plan.md step 41). Reachable in 4 clicks: state -> district ->
 * facility, each a single click through MapView's breadcrumb nodes.
 */
import { useEffect, useState } from "react";
import MapView, { DrillLevel } from "@/components/MapView";
import AlertList, { Alert } from "@/components/AlertList";
import { api, DistrictSummaryRow } from "@/lib/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DistrictSummaryRow[]>([]);

  useEffect(() => {
    api.districtSummary().then(setSummary).catch(() => setSummary([]));
  }, []);

  const root: DrillLevel = {
    id: "national",
    label: "India",
    children: [
      {
        id: "mh",
        label: "Maharashtra",
        children: summary
          .filter((r) => r.district_id.startsWith("mh/"))
          .map((r) => ({
            id: r.district_id,
            label: r.district_id.split("/")[1],
            children: [{ id: `${r.district_id}-facilities`, label: `${r.facilities_reporting} facilities reporting` }],
          })),
      },
    ],
  };

  const alerts: Alert[] = summary
    .filter((r) => r.facilities_at_risk > 0)
    .map((r) => ({ id: r.district_id, text: `${r.district_id}: ${r.facilities_at_risk} facilities at risk`, severity: "warning" }));

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">National Dashboard</h1>
      <div className="grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2">
          <MapView root={root} />
        </div>
        <div>
          <h2 className="mb-2 font-medium">Alerts</h2>
          <AlertList alerts={alerts} />
        </div>
      </div>
    </div>
  );
}
