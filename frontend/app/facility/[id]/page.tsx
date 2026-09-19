/**
 * Single-facility drill-down page (modular-plan.md step 43): stock,
 * forecast and check-in history for one facility. Server component --
 * no client interactivity needed beyond navigation. Next.js 15 passes
 * route params as a Promise.
 */
export default async function FacilityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">Facility {id}</h1>
      <p className="text-sm text-gray-500">
        Stock records, forecasts, and staff check-ins for this facility load here from the officer API
        (backend/agent/tools.py's get_stock/get_forecast, or a dedicated facility endpoint once wired to a
        real deployment).
      </p>
    </div>
  );
}
