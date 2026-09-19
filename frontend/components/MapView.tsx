"use client";
/**
 * Map-first dashboard drill-down (project.md FR9, modular-plan.md step
 * 41). A real deployment uses Google Maps JS API (architecture.md §1);
 * this renders a simple clickable list-as-map placeholder so the
 * drill-down structure (national -> state -> district -> facility) works
 * and is testable without a Maps API key.
 */
import { useState } from "react";

export interface DrillLevel {
  id: string;
  label: string;
  children?: DrillLevel[];
}

export default function MapView({ root }: { root: DrillLevel }) {
  const [path, setPath] = useState<DrillLevel[]>([root]);
  const current = path[path.length - 1];

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
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(current.children || []).map((child) => (
          <button
            key={child.id}
            className="rounded border bg-white p-3 text-left hover:bg-blue-50"
            onClick={() => child.children && setPath([...path, child])}
            data-testid={`map-node-${child.id}`}
          >
            {child.label}
          </button>
        ))}
      </div>
      {!current.children?.length && <p className="text-sm text-gray-500">No further drill-down at this level.</p>}
    </div>
  );
}
