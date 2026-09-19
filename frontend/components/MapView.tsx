"use client";
/**
 * Map-first dashboard drill-down (project.md FR9): national -> state ->
 * district -> facility. A real deployment uses Google Maps JS API
 * (architecture.md §1); this clickable grid keeps the same drill-down
 * working without a Maps API key. A node can carry static children, load
 * them on click, or link out.
 */
import { useState } from "react";

export interface DrillLevel {
  id: string;
  label: string;
  tone?: "risk" | "ok";
  href?: string;
  children?: DrillLevel[];
  load?: () => Promise<DrillLevel[]>;
}

export default function MapView({ root }: { root: DrillLevel }) {
  const [path, setPath] = useState<DrillLevel[]>([root]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = path.length === 1 ? root : path[path.length - 1];

  async function open(child: DrillLevel) {
    setError(null);
    if (child.children) return setPath([...path, child]);
    if (!child.load) return;
    setLoading(true);
    try {
      setPath([...path, { ...child, children: await child.load() }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const tone = { risk: "border-red-300 bg-red-50", ok: "bg-white" };

  return (
    <div data-testid="map-view">
      <div className="mb-2 flex gap-1 text-sm text-gray-500" data-testid="map-breadcrumb">
        {path.map((level, i) => (
          <span key={level.id}>
            {i > 0 && " > "}
            <button className="underline" onClick={() => setPath(path.slice(0, i + 1))}>
              {level.label}
            </button>
          </span>
        ))}
      </div>
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
      {loading && <p className="mb-2 text-sm text-gray-500">Loading…</p>}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(current.children || []).map((child) => {
          const className = `rounded border p-3 text-left text-sm hover:bg-blue-50 ${tone[child.tone || "ok"]}`;
          return child.href ? (
            <a key={child.id} href={child.href} className={className} data-testid={`map-node-${child.id}`}>
              {child.label}
            </a>
          ) : (
            <button key={child.id} className={className} onClick={() => open(child)} data-testid={`map-node-${child.id}`}>
              {child.label}
            </button>
          );
        })}
      </div>
      {!current.children?.length && !loading && <p className="text-sm text-gray-500">No further drill-down at this level.</p>}
    </div>
  );
}
