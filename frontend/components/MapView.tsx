"use client";
/**
 * Region drill-down: national -> state -> district -> facility. Tiles can
 * carry static children, load them on click, or link to a facility page.
 */
import Link from "next/link";
import { useState } from "react";
import { CaretRight, MapPin, Warning } from "@phosphor-icons/react";
import { useI18n } from "@/lib/i18n";
import { Skeleton } from "./ui";

export interface DrillLevel {
  id: string;
  label: string;
  sub?: string;
  tone?: "risk" | "ok";
  href?: string;
  children?: DrillLevel[];
  load?: () => Promise<DrillLevel[]>;
}

// A district has hundreds of facilities; render a page at a time instead of all at once.
const PAGE = 40;

export default function MapView({ root }: { root: DrillLevel }) {
  const { t } = useI18n();
  const [path, setPath] = useState<DrillLevel[]>([root]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState(PAGE);
  const current = path.length === 1 ? root : path[path.length - 1];

  async function open(child: DrillLevel) {
    setError(null);
    setLimit(PAGE);
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

  const tileClass = (tone?: "risk" | "ok") =>
    `group flex w-full items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition hover:border-teal-600 hover:bg-teal-50/60 dark:hover:border-teal-400 dark:hover:bg-teal-950/30 ${
      tone === "risk" ? "border-rose-200 dark:border-rose-900/70" : "border-zinc-200 dark:border-zinc-800"
    }`;

  const tileBody = (child: DrillLevel) => (
    <>
      {child.tone === "risk" ? (
        <Warning size={16} weight="fill" className="mt-0.5 shrink-0 text-rose-600 dark:text-rose-400" />
      ) : (
        <MapPin size={16} className="mt-0.5 shrink-0 text-teal-700 dark:text-teal-400" />
      )}
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{child.label}</span>
        {child.sub && <span className="muted block truncate text-xs">{child.sub}</span>}
      </span>
      <CaretRight size={14} className="mt-1 shrink-0 text-zinc-400 transition group-hover:translate-x-0.5" />
    </>
  );

  return (
    <div data-testid="map-view">
      <div className="mb-3 flex flex-wrap items-center gap-1 text-sm" data-testid="map-breadcrumb">
        {path.map((level, i) => (
          <span key={level.id} className="flex items-center gap-1">
            {i > 0 && <CaretRight size={12} className="text-zinc-400" />}
            <button
              className={i === path.length - 1 ? "font-medium" : "muted hover:text-teal-700 dark:hover:text-teal-400"}
              onClick={() => {
                setPath(path.slice(0, i + 1));
                setLimit(PAGE);
              }}
            >
              {level.label}
            </button>
          </span>
        ))}
      </div>
      {error && <p className="mb-3 rounded-lg bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">{error}</p>}
      {loading ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-12" />)}
        </div>
      ) : (
        <div className="grid max-h-[340px] gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          {(current.children || []).slice(0, limit).map((child) =>
            child.href ? (
              <Link key={child.id} href={child.href} className={tileClass(child.tone)} data-testid={`map-node-${child.id}`}>
                {tileBody(child)}
              </Link>
            ) : (
              <button key={child.id} className={tileClass(child.tone)} onClick={() => open(child)} data-testid={`map-node-${child.id}`}>
                {tileBody(child)}
              </button>
            ),
          )}
        </div>
      )}
      {(current.children?.length ?? 0) > limit && !loading && (
        <button className="btn-secondary mt-3 w-full" onClick={() => setLimit((n) => n + PAGE)}>
          {t("show_more_facilities", { n: Math.min(PAGE, (current.children?.length ?? 0) - limit) })}
        </button>
      )}
      {!current.children?.length && !loading && <p className="muted text-sm">{t("no_drill")}</p>}
    </div>
  );
}
