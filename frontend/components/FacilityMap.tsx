"use client";
/**
 * Facility map on OpenStreetMap tiles (no API key; attribution required),
 * greyscaled in light mode and inverted in dark mode by CSS (.map-tiles in
 * globals.css) so the risk markers carry all the colour. Officers see each
 * facility coloured by what it needs (a transfer, or only a district-wide supply
 * order) and can open it; the public version shows locations only, matching the
 * public view's privacy rule.
 * `flows` draws planned transfers as animated lines from source to destination;
 * facilities outside `focus` are then dimmed so the routes stand out.
 * Loaded with next/dynamic (ssr: false) because Leaflet needs `window`.
 */
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import { useRouter } from "next/navigation";

export interface MapPoint {
  lat: number;
  lon: number;
  id?: string;
  name?: string;
  tone?: Tone; // undefined = public (no stock data)
  changed?: boolean; // its shortage is fixed by the planned transfers: drawn with a pulsing ring
}

export type Tone = "ok" | "gap" | "act";

export interface Flow {
  from: [number, number];
  to: [number, number];
}

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// act = short of something a transfer can fix; gap = short only of district-wide gaps
export const TONE_COLORS: Record<Tone, { light: string; dark: string }> = {
  ok: { light: "#0f766e", dark: "#5eead4" },
  gap: { light: "#d97706", dark: "#fbbf24" },
  act: { light: "#e11d48", dark: "#fb7185" },
};
const RANK: Record<Tone, number> = { ok: 0, gap: 1, act: 2 };

function useDarkTheme() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const read = () => setDark(document.documentElement.classList.contains("dark"));
    read();
    window.addEventListener("aushadhinet:theme", read);
    return () => window.removeEventListener("aushadhinet:theme", read);
  }, []);
  return dark;
}

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    map.flyToBounds(points.map((p) => [p.lat, p.lon] as [number, number]), { padding: [24, 24], duration: 0.8 });
  }, [map, points]);
  return null;
}

export default function FacilityMap({ points, flows = [], focus, openLabel }: { points: MapPoint[]; flows?: Flow[]; focus?: Set<string>; openLabel?: string }) {
  const dark = useDarkTheme();
  const router = useRouter();
  // Least severe first so the worst facilities render on top.
  const ordered = useMemo(() => [...points].sort((a, b) => RANK[a.tone ?? "ok"] - RANK[b.tone ?? "ok"]), [points]);
  const color = (p: MapPoint) => TONE_COLORS[p.tone ?? "ok"][dark ? "dark" : "light"];
  const radius = (p: MapPoint) => (p.tone === undefined ? 3.5 : p.tone === "act" ? 7 : p.tone === "gap" ? 4.5 : 3.5);
  const fitTo = useMemo(() => (focus ? points.filter((p) => p.id && focus.has(p.id)) : points), [points, focus]);
  const flowColor = TONE_COLORS.ok[dark ? "dark" : "light"];

  return (
    <MapContainer center={[20.0, 73.9]} zoom={9} scrollWheelZoom={false} className="h-full w-full" attributionControl>
      <TileLayer url={TILES} attribution={ATTRIBUTION} className="map-tiles" />
      <FitBounds points={fitTo} />
      {ordered.map((p, i) => (
        <CircleMarker
          key={p.id ?? i}
          center={[p.lat, p.lon]}
          radius={radius(p)}
          pathOptions={{ color: color(p), fillColor: color(p), ...(focus && p.id && !focus.has(p.id) ? { fillOpacity: 0.15, opacity: 0.25 } : { fillOpacity: 0.85, opacity: 1 }), weight: 1 }}
          eventHandlers={p.id ? { click: () => router.push(`/facility/${p.id}`) } : undefined}
        >
          {p.name && (
            <Tooltip direction="top" offset={[0, -4]}>
              <span className="font-medium">{p.name}</span>
              {openLabel && <span className="block text-[11px] opacity-70">{openLabel}</span>}
            </Tooltip>
          )}
        </CircleMarker>
      ))}
      {points.filter((p) => p.changed).map((p) => (
        <CircleMarker key={`c${p.id}`} center={[p.lat, p.lon]} radius={10} interactive={false} pathOptions={{ color: flowColor, fill: false, weight: 2, className: "pulse-ring" }} />
      ))}
      {flows.map((f, i) => (
        <Polyline key={`f${i}`} positions={[f.from, f.to]} pathOptions={{ color: flowColor, weight: 3, opacity: 1, className: "flow-line" }} interactive={false} />
      ))}
    </MapContainer>
  );
}
