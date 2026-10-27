"use client";
/**
 * Public transparency view: district totals only, from backend/api/public.py,
 * the same endpoints the tests prove never return a facility identifier. Live
 * districts show shortages split the way officers act on them (district-wide,
 * needing a supply order, or fixable by transfer); "Across India" shows every
 * state in the national facility directory and what is live there today.
 */
import { useEffect, useState } from "react";
import { Buildings } from "@phosphor-icons/react";
import { CountUp, Notice, PageHeader, Reveal, Skeleton, Stat } from "@/components/ui";
import { api, CoverageRow, DistrictSummaryRow, FederatedModel } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function PublicPage() {
  const { t, num, drug, place } = useI18n();
  const [rows, setRows] = useState<DistrictSummaryRow[] | null>(null);
  const [states, setStates] = useState<CoverageRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fed, setFed] = useState<FederatedModel | null>(null);

  useEffect(() => {
    api.districtSummary().then(setRows).catch((e) => setError((e as Error).message));
    api.coverage().then(setStates).catch((e) => setError((e as Error).message));
    api.federated().then(setFed).catch(() => setFed(null)); // optional: the page works without it
  }, []);

  const live = (rows ?? []).filter((r) => r.facilities_reporting > 0);
  const reporting = live.reduce((a, r) => a + r.facilities_reporting, 0);
  const transfer = live.reduce((a, r) => a + r.facilities_needing_transfer, 0);
  const gaps = new Set(live.flatMap((r) => Object.keys(r.escalate)));
  const byDrug: Record<string, number> = {};
  live.forEach((r) => Object.entries(r.at_risk_by_drug).forEach(([d, c]) => (byDrug[d] = (byDrug[d] ?? 0) + c)));
  const drugs = Object.entries(byDrug).sort((a, b) => b[1] - a[1]);
  const ready = (states ?? []).reduce((a, s) => a + s.facilities, 0);
  const districts = (states ?? []).reduce((a, s) => a + s.districts, 0);
  const maxState = states?.[0]?.facilities ?? 1;
  const ordered = [...(states ?? [])].sort((a, b) => b.live_districts - a.live_districts || b.facilities - a.facilities);

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title={t("public_title")} sub={t("public_sub")} />
      {error && <Notice tone="error">{t("error_load", { error })}</Notice>}

      <Reveal className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {rows && states ? (
          <>
            <Stat label={t("kpi_live")} value={<CountUp value={live.length} format={num} />} hint={t("kpi_live_hint", { n: num(reporting) })} />
            <Stat label={t("kpi_escalate")} value={<CountUp value={gaps.size} format={num} />} hint={t("kpi_escalate_hint")} tone="warn" />
            <Stat label={t("kpi_transfer")} value={<CountUp value={transfer} format={num} />} hint={t("kpi_transfer_hint")} tone="risk" />
            <Stat label={t("kpi_ready")} value={<CountUp value={ready} format={num} />} hint={t("kpi_ready_hint", { districts: num(districts) })} />
          </>
        ) : (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[104px] rounded-xl" />)
        )}
      </Reveal>

      <Reveal delay={0.06} className="card mt-6 overflow-hidden">
        <h2 className="h2 px-4 pt-4">{t("public_live_title")}</h2>
        <div className="overflow-x-auto">
          <table className="mt-2 w-full text-sm" data-testid="public-table">
            <thead className="bg-zinc-50 text-left dark:bg-zinc-800/50">
              <tr>
                <th className="label px-4 py-3 font-medium">{t("public_col_district")}</th>
                <th className="label px-4 py-3 text-right font-medium">{t("public_col_reporting")}</th>
                <th className="label px-4 py-3 font-medium">{t("kpi_escalate")}</th>
                <th className="label px-4 py-3 text-right font-medium">{t("kpi_transfer")}</th>
              </tr>
            </thead>
            <tbody>
              {live.map((r) => (
                <tr key={r.district_id} className="border-t border-zinc-100 align-top dark:border-zinc-800">
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2 font-medium">
                      <Buildings size={16} className="text-teal-700 dark:text-teal-400" /> {place(r.district_id)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{num(r.facilities_reporting)}</td>
                  <td className="px-4 py-3 text-amber-800 dark:text-amber-300">{Object.keys(r.escalate).map(drug).join(", ") || "-"}</td>
                  <td className="px-4 py-3 text-right font-medium text-rose-700 dark:text-rose-400">{num(r.facilities_needing_transfer)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>

      {drugs.length > 0 && (
        <Reveal delay={0.1} className="card mt-6 p-5">
          <h2 className="h2 mb-4">{t("public_by_medicine")}</h2>
          <ul className="grid gap-x-8 gap-y-3 md:grid-cols-2">
            {drugs.map(([id, count]) => (
              <li key={id}>
                <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
                  <span className="flex items-center gap-2 font-medium">
                    {drug(id)}
                    {gaps.has(id) && (
                      <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 ring-1 ring-inset ring-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-900">
                        {t("shortage_district_wide")}
                      </span>
                    )}
                  </span>
                  <span className="muted shrink-0 text-xs">{t("shortage_line", { count: num(count), total: num(reporting) })}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                  <div
                    className={`h-full origin-left animate-[grow_0.8s_cubic-bezier(0.16,1,0.3,1)] rounded-full ${gaps.has(id) ? "bg-amber-400 dark:bg-amber-300" : "bg-rose-500 dark:bg-rose-400"}`}
                    style={{ width: `${Math.max(2, (100 * count) / reporting)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Reveal>
      )}

      <Reveal delay={0.14} className="card mt-6 p-5" >
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="h2">{t("coverage_title")}</h2>
          {states && <span className="muted text-xs">{t("kpi_states")}: {num(states.length)}</span>}
        </div>
        <p className="muted mb-4 max-w-[70ch] text-sm leading-relaxed">{t("coverage_sub")}</p>
        {!states ? (
          <Skeleton className="h-64" />
        ) : (
          <ul className="grid gap-x-8 gap-y-2.5 md:grid-cols-2" data-testid="coverage-list">
            {ordered.map((s) => (
              <li key={s.state}>
                <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="truncate font-medium">{s.live_districts ? place(s.code) : s.state}</span>
                    {s.live_districts > 0 ? (
                      <span className="rounded-full bg-teal-600 px-1.5 py-0.5 text-[10px] font-semibold text-white dark:bg-teal-500 dark:text-zinc-950">
                        {t("coverage_live")} · {num(s.live_districts)}
                      </span>
                    ) : null}
                  </span>
                  <span className="muted shrink-0 text-xs">{t("coverage_line", { facilities: num(s.facilities), districts: num(s.districts) })}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                  <div
                    className={`h-full origin-left animate-[grow_0.8s_cubic-bezier(0.16,1,0.3,1)] rounded-full ${s.live_districts ? "bg-teal-600 dark:bg-teal-400" : "bg-zinc-300 dark:bg-zinc-600"}`}
                    style={{ width: `${Math.max(2, (100 * s.facilities) / maxState)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Reveal>
      {fed && (
        <Reveal delay={0.12} className="card mt-6 overflow-hidden" data-testid="federated-card">
          <h2 className="h2 px-4 pt-4">{t("fed_title")}</h2>
          <p className="muted px-4 pt-1 text-sm">
            {t("fed_sub", { states: fed.states.map((s) => place(s.toLowerCase())).join(" + "), rows: num(Object.values(fed.training_rows).reduce((a, b) => a + b, 0)), wape: num(fed.wape, 2), month: fed.month.slice(0, 7) })}
          </p>
          <div className="overflow-x-auto">
            <table className="mt-2 w-full text-sm">
              <thead className="bg-zinc-50 text-left dark:bg-zinc-800/50">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("fed_district")}</th>
                  <th className="px-4 py-2 font-medium">{t("fed_item")}</th>
                  <th className="px-4 py-2 text-right font-medium">{t("fed_actual")}</th>
                  <th className="px-4 py-2 text-right font-medium">{t("fed_estimate")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {fed.rows.slice(0, 8).map((r) => (
                  <tr key={`${r.district_id}-${r.drug}`}>
                    <td className="px-4 py-2">{r.district_id.split("/").pop()!.split("-").map((w) => w[0].toUpperCase() + w.slice(1)).join(" ")}</td>
                    <td className="px-4 py-2">{r.drug}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{num(r.actual)}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{r.history ? num(r.estimate) : <span className="muted">{num(r.estimate)}*</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted px-4 py-2.5 text-xs">{t("fed_note")}</p>
        </Reveal>
      )}
    </div>
  );
}
