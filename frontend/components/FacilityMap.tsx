"use client";
/**
 * Facility map on OpenStreetMap tiles (no API key; attribution required),
 * greyscaled in light mode and inverted in dark mode by CSS (.map-tiles in
 * globals.css) so the risk markers carry all the colour. Officers see each
 * facility coloured by how many medicines are short and can open it; the
 * public version shows locations only, matching the public view's privacy rule.
 * Loaded with next/dynamic (ssr: false) because Leaflet needs `window`.
 */
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import { useRouter } from "next/navigation";

export interface MapPoint {
  lat: number;
  lon: number;
  id?: string;
  name?: string;
  short?: number; // medicines under a week of cover; undefined = public (no stock data)
}

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export const SEVERITY_COLORS = {
  none: { light: "#0f766e", dark: "#5eead4" },
  one: { light: "#d97706", dark: "#fbbf24" },
  many: { light: "#e11d48", dark: "#fb7185" },
};

function severity(p: MapPoint): keyof typeof SEVERITY_COLORS {
  if (!p.short) return "none";
  return p.short === 1 ? "one" : "many";
}

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
    map.fitBounds(points.map((p) => [p.lat, p.lon] as [number, number]), { padding: [24, 24] });
  }, [map, points]);
  return null;
}

export default function FacilityMap({ points, openLabel }: { points: MapPoint[]; openLabel?: string }) {
  const dark = useDarkTheme();
  const router = useRouter();
  // Least severe first so the worst facilities render on top.
  const ordered = useMemo(() => [...points].sort((a, b) => (a.short ?? 0) - (b.short ?? 0)), [points]);
  const color = (p: MapPoint) => SEVERITY_COLORS[severity(p)][dark ? "dark" : "light"];
  const radius = (p: MapPoint) => (p.short === undefined ? 3.5 : 3 + Math.min(p.short, 3) * 1.5);

  return (
    <MapContainer center={[20.0, 73.9]} zoom={9} scrollWheelZoom={false} className="h-full w-full" attributionControl>
      <TileLayer url={TILES} attribution={ATTRIBUTION} className="map-tiles" />
      <FitBounds points={points} />
      {ordered.map((p, i) => (
        <CircleMarker
          key={p.id ?? i}
          center={[p.lat, p.lon]}
          radius={radius(p)}
          pathOptions={{ color: color(p), fillColor: color(p), fillOpacity: 0.8, weight: 1 }}
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
    </MapContainer>
  );
}
