"use client";
/**
 * One facility: latest stock per medicine, next-week demand forecast and
 * stock-out probability (backend/api/officer.py's facility_detail),
 * highest risk first.
 */
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, Buildings, Clock } from "@phosphor-icons/react";
import { Empty, Notice, Reveal, RiskBadge, riskLevel, Skeleton, Stat } from "@/components/ui";
import { api, FacilityDetail } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useI18n, type MessageKey } from "@/lib/i18n";

export default function FacilityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, ready } = useAuth();
  const { t, num, drug, place, date } = useI18n();
  const [detail, setDetail] = useState<FacilityDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) api.facilityDetail(id).then(setDetail).catch((e) => setError((e as Error).message));
  }, [id, user]);

  if (!ready) return null;
  if (!user) {
    return (
      <div className="mx-auto max-w-xl pt-8">
        <Empty icon={<Buildings size={22} />} title={id} hint={t("facility_signin", { id })} />
      </div>
    );
  }

  const back = (
    <Link href="/" className="muted mb-4 inline-flex items-center gap-1.5 text-sm hover:text-teal-700 dark:hover:text-teal-400">
      <ArrowLeft size={14} /> {t("facility_back")}
    </Link>
  );

  if (error) return <div className="mx-auto max-w-5xl">{back}<Notice tone="error">{error}</Notice></div>;
  if (!detail) {
    return (
      <div className="mx-auto max-w-5xl space-y-4" aria-label={t("facility_loading", { id })}>
        {back}
        <Skeleton className="h-9 w-80" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[104px] rounded-xl" />)}</div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  const latest = new Map<string, FacilityDetail["stock"][number]>();
  for (const s of detail.stock) {
    const prev = latest.get(s.drug_id);
    if (!prev || s.as_of_date >= prev.as_of_date) latest.set(s.drug_id, s);
  }
  const forecast = new Map(detail.forecasts.map((f) => [f.drug_id, f]));
  const rows = Array.from(latest.values()).sort((a, b) => (forecast.get(b.drug_id)?.stockout_prob ?? 0) - (forecast.get(a.drug_id)?.stockout_prob ?? 0));
  const high = rows.filter((r) => (forecast.get(r.drug_id)?.stockout_prob ?? 0) >= 0.5).length;
  const f = detail.facility;
  const asOf = rows.reduce((m, r) => (r.as_of_date > m ? r.as_of_date : m), "");

  return (
    <div className="mx-auto max-w-5xl">
      {back}
      <Reveal>
        <h1 className="h1">{f.name}</h1>
        <p className="muted mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span className="font-mono" translate="no">{f.facility_id}</span>
          <span>{t(`type_${f.facility_type}` as MessageKey)}</span>
          <span>{Array.from(new Set([f.block, place(f.district_id)].filter(Boolean))).join(", ")}</span>
        </p>
      </Reveal>

      <Reveal delay={0.06} className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3">
        <Stat label={t("facility_kpi_items")} value={num(rows.length)} />
        <Stat label={t("facility_kpi_high")} value={num(high)} tone={high ? "risk" : "neutral"} />
        <Stat label={t("col_as_of")} value={<span className="flex items-center gap-2 text-lg md:text-xl"><Clock size={20} className="text-zinc-400" />{asOf ? date(asOf) : "-"}</span>} />
      </Reveal>

      <Reveal delay={0.12} className="card mt-6 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm" data-testid="facility-stock">
          <thead className="bg-zinc-50 text-left dark:bg-zinc-800/50">
            <tr>
              <th className="label px-4 py-3 font-medium">{t("col_medicine")}</th>
              <th className="label px-4 py-3 text-right font-medium">{t("col_on_hand")}</th>
              <th className="label px-4 py-3 font-medium">{t("col_as_of")}</th>
              <th className="label px-4 py-3 font-medium">{t("col_demand")}</th>
              <th className="label px-4 py-3 font-medium">{t("col_risk")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => {
              const fc = forecast.get(s.drug_id);
              const prob = fc?.stockout_prob ?? 0;
              const cover = fc && fc.p90 > 0 ? Math.min(1, s.on_hand / fc.p90) : 1;
              return (
                <tr key={s.drug_id} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-4 py-3">
                    <span className="font-medium">{drug(s.drug_id)}</span>
                    {s.status !== "confirmed" && <span className="ml-2 rounded-full bg-amber-50 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">{t("pending")}</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">{num(s.on_hand)}</td>
                  <td className="muted whitespace-nowrap px-4 py-3">{date(s.as_of_date)}</td>
                  <td className="px-4 py-3">
                    {fc ? (
                      <div className="flex items-center gap-3">
                        <span className="w-24 shrink-0">
                          {num(fc.p50)} <span className="muted text-xs">({num(fc.p10)}-{num(fc.p90)})</span>
                        </span>
                        <span className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-zinc-100 sm:block dark:bg-zinc-800" title={`${Math.round(cover * 100)}%`}>
                          <span className={`block h-full rounded-full ${prob >= 0.5 ? "bg-rose-500" : prob >= 0.2 ? "bg-amber-400" : "bg-teal-600 dark:bg-teal-400"}`} style={{ width: `${cover * 100}%` }} />
                        </span>
                      </div>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {fc ? (
                      <span className="flex items-center gap-2">
                        <RiskBadge level={riskLevel(prob)} />
                        <span className="muted text-xs">{num(prob * 100)}%</span>
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Reveal>
    </div>
  );
}
