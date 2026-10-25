"use client";
/**
 * Overview. Officers get a morning briefing: medicines short across the whole
 * district (only a supply order fixes those, so they are escalated with a
 * quantity) and stock that can move between facilities (drafted transfers),
 * with a map that can show the district before and after those transfers, then
 * today's beds and staff.
 * Anonymous visitors see what the system is, district totals, a
 * locations-only map and the three-step story.
 */
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Check, ClipboardText, Copy, Eye, Lightning, Megaphone, Truck, WhatsappLogo } from "@phosphor-icons/react";
import MapView, { DrillLevel } from "@/components/MapView";
import CapacityCard from "@/components/CapacityCard";
import HowItWorks from "@/components/HowItWorks";
import { CountUp, Reveal, Skeleton, Stat } from "@/components/ui";
import type { Flow, MapPoint, Tone } from "@/components/FacilityMap";
import { api, CoverageRow, DistrictSummaryRow, FacilitySummary, TransferOrder } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useI18n } from "@/lib/i18n";

const FacilityMap = dynamic(() => import("@/components/FacilityMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-none" />,
});

const PILOT = "mh/nashik";

/** act: short of something nearby surplus can fix; gap: short only of district-wide gaps. */
function toneOf(f: FacilitySummary, gaps: Record<string, number>, covered: Set<string>): Tone {
  const open = f.short_drugs.filter((d) => !covered.has(`${f.facility_id}|${d}`));
  if (open.some((d) => !(d in gaps))) return "act";
  return open.length ? "gap" : "ok";
}

export default function DashboardPage() {
  const { t, num, drug, drugIds, place } = useI18n();
  const { user, ready } = useAuth();
  const [summary, setSummary] = useState<DistrictSummaryRow[] | null>(null);
  const [states, setStates] = useState<CoverageRow[] | null>(null);
  const [facilities, setFacilities] = useState<FacilitySummary[] | null>(null);
  const [publicPoints, setPublicPoints] = useState<MapPoint[] | null>(null);
  const [drafts, setDrafts] = useState<TransferOrder[] | null>(null);
  const [after, setAfter] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const district = user && user.jurisdiction.includes("/") ? user.jurisdiction : PILOT;

  useEffect(() => {
    api.districtSummary().then(setSummary).catch((e) => setError((e as Error).message));
    api.coverage().then(setStates).catch(() => setStates([]));
  }, []);

  useEffect(() => {
    if (!ready) return;
    if (user) {
      api.districtFacilities(district).then(setFacilities).catch(() => setFacilities([]));
      api.listOrders(district).then((os) => setDrafts(os.filter((o) => o.status === "draft"))).catch(() => setDrafts([]));
    } else {
      api.facilityPoints(PILOT).then((ps) => setPublicPoints(ps.map(([lat, lon]) => ({ lat, lon })))).catch(() => setPublicPoints([]));
    }
  }, [ready, user, district]);

  const row = summary?.find((r) => r.district_id === district) ?? summary?.[0];
  const gaps = useMemo(() => row?.escalate ?? {}, [row]);
  const topDrugs = useMemo(() => Object.entries(row?.at_risk_by_drug ?? {}).slice(0, 8), [row]);
  const maxCount = topDrugs[0]?.[1] ?? 1;
  const reporting = row?.facilities_reporting ?? 0;

  const byId = useMemo(() => new Map((facilities ?? []).map((f) => [f.facility_id, f])), [facilities]);
  const covered = useMemo(() => new Set((drafts ?? []).map((o) => `${o.to_facility_id}|${o.drug_id}`)), [drafts]);
  const none = useMemo(() => new Set<string>(), []);
  const points: MapPoint[] | null = useMemo(
    () => (user ? facilities && facilities.map((f) => {
      const tone = toneOf(f, gaps, after ? covered : none);
      return { lat: f.lat, lon: f.lon, id: f.facility_id, name: f.name, tone, changed: after && tone !== "act" && toneOf(f, gaps, none) === "act" };
    }) : publicPoints),
    [user, facilities, publicPoints, gaps, after, covered, none],
  );
  const flows: Flow[] = after
    ? (drafts ?? []).flatMap((o) => {
        const a = byId.get(o.from_facility_id), b = byId.get(o.to_facility_id);
        return a && b ? [{ from: [a.lat, a.lon], to: [b.lat, b.lon] } as Flow] : [];
      })
    : [];
  const focus = useMemo(() => (after ? new Set((drafts ?? []).flatMap((o) => [o.from_facility_id, o.to_facility_id])) : undefined), [after, drafts]);
  const actToday = (facilities ?? []).filter((f) => toneOf(f, gaps, none) === "act").length;
  const actAfter = (facilities ?? []).filter((f) => toneOf(f, gaps, covered) === "act").length;

  async function propose() {
    setBusy(true);
    try {
      setDrafts(await api.proposeOrders(district));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function copyRequest() {
    const lines = Object.entries(gaps).map(([id, weeks]) =>
      t("request_line", { drug: drug(id), units: num(row?.procurement_units[id] ?? 0), weeks: num(weeks, 1) }));
    await navigator.clipboard.writeText([t("request_header", { district: place(district) }), ...lines].join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const root: DrillLevel = {
    id: "national",
    label: t("india"),
    // Live states (with reporting districts) open; every other state in the directory is shown as ready to onboard.
    children: [...(states ?? [])]
      .sort((a, b) => b.live_districts - a.live_districts || b.facilities - a.facilities)
      .map((s): DrillLevel => {
        const sub = t("coverage_line", { facilities: num(s.facilities), districts: num(s.districts) });
        if (!s.live_districts) return { id: `${s.code}-${s.state}`, label: s.state, tone: "idle", sub: `${sub} · ${t("coverage_ready")}` };
        return {
          id: s.code,
          label: place(s.code),
          sub,
          children: (summary ?? [])
            .filter((r) => r.district_id.startsWith(`${s.code}/`))
            .map((r) => ({
              id: r.district_id,
              label: place(r.district_id),
              sub: `${t("kpi_live_hint", { n: num(r.facilities_reporting) })} · ${t("kpi_transfer").toLowerCase()}: ${num(r.facilities_needing_transfer)}`,
              tone: r.facilities_needing_transfer ? "risk" : "ok",
              load: async () => {
                if (!user) throw new Error(t("signin_for_facilities"));
                const fs = await api.districtFacilities(r.district_id);
                const act = (f: FacilitySummary) => f.short_drugs.some((d) => !(d in r.escalate));
                return fs
                  .sort((a, b) => Number(act(b)) - Number(act(a)))
                  .map((f) => ({
                    id: f.facility_id,
                    label: f.name,
                    sub: `${f.facility_id} · ${f.block ?? ""}`,
                    tone: act(f) ? "risk" : "ok",
                    href: `/facility/${f.facility_id}`,
                  }));
              },
            })),
        };
      }),
  };

  const gapCount = Object.keys(gaps).length;

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-12">
        <Reveal className="flex flex-col gap-6 lg:col-span-5">
          <div>
            <h1 className="text-balance text-3xl font-semibold leading-[1.15] tracking-tight md:text-4xl">
              {user ? t("home_title_signed", { district: place(district) }) : t("home_title", { n: num(reporting || 760) })}
            </h1>
            <p className="muted mt-3 max-w-[52ch] leading-relaxed">{user ? t("home_sub_signed") : t("home_sub")}</p>
            {!user && (
              <div className="mt-5 flex flex-wrap gap-2">
                <Link href="/sim" className="btn-primary">
                  <WhatsappLogo size={16} weight="fill" /> {t("cta_simulator")}
                </Link>
                <Link href="/public" className="btn-secondary">
                  <Eye size={16} /> {t("cta_public")}
                </Link>
              </div>
            )}
          </div>

          {user ? (
            <div className="space-y-4" data-testid="briefing">
              <div className="card border-l-4 border-l-amber-500 p-4 dark:border-l-amber-400">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="h2 flex items-center gap-2">
                    <Megaphone size={18} weight="duotone" className="text-amber-600 dark:text-amber-400" /> {t("brief_escalate_title")}
                  </h2>
                  {gapCount > 0 && (
                    <button className="btn-secondary px-2.5 py-1 text-xs" onClick={copyRequest} data-testid="copy-request">
                      {copied ? <Check size={14} weight="bold" /> : <Copy size={14} />} {copied ? t("brief_copied") : t("brief_copy")}
                    </button>
                  )}
                </div>
                {!row ? (
                  <Skeleton className="mt-3 h-20" />
                ) : gapCount ? (
                  <>
                    <p className="muted mt-1.5 text-sm leading-relaxed">{t("brief_escalate_sub", { n: num(gapCount) })}</p>
                    <ul className="mt-3 divide-y divide-zinc-100 text-sm dark:divide-zinc-800" data-testid="escalate-list">
                      {Object.entries(gaps).map(([id, weeks]) => (
                        <li key={id} className="flex flex-wrap items-baseline justify-between gap-x-3 py-1.5">
                          <span className="font-medium">{drug(id)}</span>
                          <span className="muted text-xs">{t("brief_escalate_line", { weeks: num(weeks, 1), units: num(row.procurement_units[id] ?? 0) })}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="muted mt-1.5 text-sm">{t("brief_none")}</p>
                )}
              </div>

              <div className="card border-l-4 border-l-rose-500 p-4 dark:border-l-rose-400">
                <h2 className="h2 flex items-center gap-2">
                  <Truck size={18} weight="duotone" className="text-rose-600 dark:text-rose-400" /> {t("brief_move_title")}
                </h2>
                {!drafts || !row ? (
                  <Skeleton className="mt-3 h-12" />
                ) : (
                  <>
                    <p className="muted mt-1.5 text-sm leading-relaxed">
                      {drafts.length
                        ? t("brief_move_drafts", { n: num(drafts.length), m: num(new Set(drafts.map((o) => o.to_facility_id)).size) })
                        : t("brief_move_none", { n: num(row.facilities_needing_transfer) })}
                    </p>
                    <div className="mt-3">
                      {drafts.length ? (
                        <Link href="/orders" className="btn-primary">
                          <ClipboardText size={16} /> {t("brief_move_cta")}
                        </Link>
                      ) : (
                        <button className="btn-primary" disabled={busy} onClick={propose}>
                          <Lightning size={16} weight="fill" /> {busy ? t("working") : t("propose")}
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {row ? (
                <>
                  <Stat label={t("kpi_reporting")} value={<CountUp value={reporting} format={num} />} />
                  <Stat label={t("kpi_escalate")} value={<CountUp value={gapCount} format={num} />} hint={t("kpi_escalate_hint")} tone="warn" />
                  <Stat label={t("kpi_transfer")} value={<CountUp value={row.facilities_needing_transfer} format={num} />} hint={t("kpi_transfer_hint")} tone="risk" />
                  <Stat label={t("kpi_medicines")} value={<CountUp value={drugIds.length || 16} format={num} />} />
                </>
              ) : (
                Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[104px] rounded-xl" />)
              )}
            </div>
          )}
          {error && <p className="text-sm text-rose-700 dark:text-rose-400">{t("error_load", { error })}</p>}
        </Reveal>

        <Reveal delay={0.08} className="lg:col-span-7">
          <div className="card flex h-full flex-col overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200/80 px-4 py-3 dark:border-zinc-800">
              <h2 className="h2">
                {t("map_title")}, {place(district)}
              </h2>
              {user ? (
                drafts && drafts.length > 0 && (
                  <div className="flex rounded-lg border border-zinc-300 p-0.5 text-xs dark:border-zinc-700" role="group" data-testid="map-mode">
                    {[false, true].map((mode) => (
                      <button
                        key={String(mode)}
                        aria-pressed={after === mode}
                        onClick={() => setAfter(mode)}
                        className={`rounded-md px-2.5 py-1 font-medium transition ${after === mode ? "bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950" : "muted hover:text-zinc-900 dark:hover:text-zinc-100"}`}
                      >
                        {mode ? t("map_after") : t("map_today")}
                      </button>
                    ))}
                  </div>
                )
              ) : (
                <span className="muted text-xs">{t("map_public_note")}</span>
              )}
            </div>
            {user && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-zinc-200/80 px-4 py-2 text-xs dark:border-zinc-800">
                <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-rose-600 dark:bg-rose-400" /> {t("map_legend_act")}</span>
                <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-amber-600 dark:bg-amber-400" /> {t("map_legend_gap")}</span>
                <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-teal-700 dark:bg-teal-300" /> {t("map_legend_ok")}</span>
                {after && actToday > 0 && (
                  <span className="ml-auto font-medium text-teal-700 dark:text-teal-400" data-testid="map-after-note">
                    {t("map_after_note", { n: num(actToday - actAfter), m: num(actToday) })}
                  </span>
                )}
              </div>
            )}
            {/* isolate: Leaflet panes use z-index 400+, which would otherwise cover the sticky header */}
            <div className="relative isolate h-[380px] md:h-[460px] lg:h-full lg:min-h-[460px]">
              {points ? <FacilityMap points={points} flows={flows} focus={focus} openLabel={user ? t("map_open_facility") : undefined} /> : <Skeleton className="h-full w-full rounded-none" />}
            </div>
          </div>
        </Reveal>
      </section>

      {user ? (
        <Reveal delay={0.1}>
          <CapacityCard district={district} />
        </Reveal>
      ) : (
        <Reveal delay={0.1}>
          <HowItWorks />
        </Reveal>
      )}

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
                    <span className="flex items-center gap-2 font-medium">
                      {drug(id)}
                      {id in gaps && (
                        <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 ring-1 ring-inset ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900">
                          {t("shortage_district_wide")}
                        </span>
                      )}
                    </span>
                    <span className="muted shrink-0 text-xs">{t("shortage_line", { count: num(count), total: num(reporting) })}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                    <div
                      className={`h-full origin-left animate-[grow_0.8s_cubic-bezier(0.16,1,0.3,1)] rounded-full ${id in gaps ? "bg-amber-400 dark:bg-amber-300" : "bg-rose-500 dark:bg-rose-400"}`}
                      style={{ width: `${Math.max(2, (100 * count) / maxCount)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted text-sm">{t("shortages_empty")}</p>
          )}
        </Reveal>

        <Reveal delay={0.16} className="card p-5 lg:col-span-5">
          <h2 className="h2 mb-3">{t("regions_title")}</h2>
          {summary && states ? <MapView root={root} /> : <Skeleton className="h-40" />}
        </Reveal>
      </section>
    </div>
  );
}
