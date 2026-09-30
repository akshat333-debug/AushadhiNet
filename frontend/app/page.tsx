"use client";
/**
 * Overview. Anonymous visitors see what the system is, district totals and a
 * locations-only map; officers see their district's facilities coloured by
 * stock-out risk, and can drill down region by region.
 */
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ClipboardText, Eye, WhatsappLogo } from "@phosphor-icons/react";
import MapView, { DrillLevel } from "@/components/MapView";
import { Reveal, Skeleton, Stat } from "@/components/ui";
import type { MapPoint } from "@/components/FacilityMap";
import { api, DistrictSummaryRow } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useI18n } from "@/lib/i18n";

const FacilityMap = dynamic(() => import("@/components/FacilityMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-none" />,
});

const PILOT = "mh/nashik";

export default function DashboardPage() {
  const { t, num, drug, drugIds, place } = useI18n();
  const { user, ready } = useAuth();
  const [summary, setSummary] = useState<DistrictSummaryRow[] | null>(null);
  const [points, setPoints] = useState<MapPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const district = user && user.jurisdiction.includes("/") ? user.jurisdiction : PILOT;

  useEffect(() => {
    api.districtSummary().then(setSummary).catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!ready) return;
    const load = user
      ? api.districtFacilities(district).then((fs) => fs.map((f) => ({ lat: f.lat, lon: f.lon, id: f.facility_id, name: f.name, short: f.short_count })))
      : api.facilityPoints(PILOT).then((ps) => ps.map(([lat, lon]) => ({ lat, lon })));
    load.then(setPoints).catch(() => setPoints([]));
  }, [ready, user, district]);

  const row = summary?.find((r) => r.district_id === district) ?? summary?.[0];
  const topDrugs = useMemo(() => Object.entries(row?.at_risk_by_drug ?? {}).slice(0, 8), [row]);
  const maxCount = topDrugs[0]?.[1] ?? 1;

  const root: DrillLevel = {
    id: "national",
    label: t("india"),
    children: Array.from(new Set((summary ?? []).map((r) => r.district_id.split("/")[0]))).map((code) => ({
      id: code,
      label: place(code),
      children: (summary ?? [])
        .filter((r) => r.district_id.startsWith(`${code}/`))
        .map((r) => ({
          id: r.district_id,
          label: place(r.district_id),
          sub: t("district_tile_sub", { risk: num(r.facilities_at_risk), total: num(r.facilities_reporting) }),
          tone: r.facilities_at_risk ? "risk" : "ok",
          load: async () => {
            if (!user) throw new Error(t("signin_for_facilities"));
            const facilities = await api.districtFacilities(r.district_id);
            return facilities
              .sort((a, b) => Number(b.at_risk) - Number(a.at_risk))
              .map((f) => ({
                id: f.facility_id,
                label: f.name,
                sub: `${f.facility_id} · ${f.block ?? ""}`,
                tone: f.at_risk ? "risk" : "ok",
                href: `/facility/${f.facility_id}`,
              }));
          },
        })),
    })),
  };

  const reporting = row?.facilities_reporting ?? 0;
  const atRisk = row?.facilities_at_risk ?? 0;

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-12">
        <Reveal className="flex flex-col gap-8 lg:col-span-5">
          <div>
            <h1 className="text-balance text-3xl font-semibold leading-[1.15] tracking-tight md:text-4xl">
              {user ? t("home_title_signed", { district: place(district) }) : t("home_title", { n: num(reporting || 760) })}
            </h1>
            <p className="muted mt-3 max-w-[52ch] leading-relaxed">{user ? t("home_sub_signed") : t("home_sub")}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {user ? (
                <Link href="/orders" className="btn-primary">
                  <ClipboardText size={16} /> {t("cta_orders")}
                </Link>
              ) : (
                <>
                  <Link href="/sim" className="btn-primary">
                    <WhatsappLogo size={16} weight="fill" /> {t("cta_simulator")}
                  </Link>
                  <Link href="/public" className="btn-secondary">
                    <Eye size={16} /> {t("cta_public")}
                  </Link>
                </>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {summary ? (
              <>
                <Stat label={t("kpi_reporting")} value={num(reporting)} />
                <Stat
                  label={t("kpi_at_risk")}
                  value={num(atRisk)}
                  hint={reporting ? `${num((100 * atRisk) / reporting)}%, ${t("kpi_at_risk_hint").toLowerCase()}` : t("kpi_at_risk_hint")}
                  tone="risk"
                />
                <Stat label={t("kpi_medicines")} value={num(drugIds.length || 16)} />
                <Stat label={t("kpi_most_short")} value={<span className="text-lg md:text-xl">{topDrugs[0] ? drug(topDrugs[0][0]) : "-"}</span>} hint={topDrugs[0] ? t("shortage_line", { count: num(topDrugs[0][1]), total: num(reporting) }) : undefined} />
              </>
            ) : (
              Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[104px] rounded-xl" />)
            )}
          </div>
          {error && <p className="text-sm text-rose-700 dark:text-rose-400">{t("error_load", { error })}</p>}
        </Reveal>

        <Reveal delay={0.08} className="lg:col-span-7">
          <div className="card flex h-full flex-col overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200/80 px-4 py-3 dark:border-zinc-800">
              <h2 className="h2">
                {t("map_title")}, {place(district)}
              </h2>
              {user ? (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                  <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-rose-600 dark:bg-rose-400" /> {t("map_legend_many")}</span>
                  <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-amber-600 dark:bg-amber-400" /> {t("map_legend_one")}</span>
                  <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-teal-700 dark:bg-teal-300" /> {t("map_legend_ok")}</span>
                </div>
              ) : (
                <span className="muted text-xs">{t("map_public_note")}</span>
              )}
            </div>
            {/* isolate: Leaflet panes use z-index 400+, which would otherwise cover the sticky header */}
            <div className="relative isolate h-[380px] md:h-[460px] lg:h-full lg:min-h-[460px]">
              {points ? <FacilityMap points={points} openLabel={user ? t("map_open_facility") : undefined} /> : <Skeleton className="h-full w-full rounded-none" />}
            </div>
          </div>
        </Reveal>
      </section>

      <section className="grid gap-6 lg:grid-cols-12">
        <Reveal delay={0.12} className="card p-5 lg:col-span-7">
          <h2 className="h2 mb-4">{t("shortages_title")}</h2>
          {!summary ? (
            <div className="space-y-3">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-8" />)}</div>
          ) : topDrugs.length ? (
            <ul className="space-y-3" data-testid="alert-list">
              {topDrugs.map(([id, count]) => (
                <li key={id}>
                  <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
                    <span className="font-medium">{drug(id)}</span>
                    <span className="muted shrink-0 text-xs">{t("shortage_line", { count: num(count), total: num(reporting) })}</span>
                  </div>
                  <div
                    className={`h-2 rounded-full ${count / reporting > 0.5 ? "bg-rose-500 dark:bg-rose-400" : "bg-amber-400 dark:bg-amber-300"}`}
                    style={{ width: `${Math.max(2, (100 * count) / maxCount)}%` }}
                  />
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted text-sm">{t("shortages_empty")}</p>
          )}
        </Reveal>

        <Reveal delay={0.16} className="card p-5 lg:col-span-5">
          <h2 className="h2 mb-3">{t("regions_title")}</h2>
          {summary ? <MapView root={root} /> : <Skeleton className="h-40" />}
        </Reveal>
      </section>
    </div>
  );
}
