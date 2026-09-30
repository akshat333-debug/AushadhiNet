"use client";
/**
 * Public transparency view: district totals only, from backend/api/public.py,
 * the same endpoint the tests prove never returns a facility identifier.
 */
import { useEffect, useState } from "react";
import { Buildings, Warning } from "@phosphor-icons/react";
import { Notice, PageHeader, Reveal, Skeleton, Stat } from "@/components/ui";
import { api, DistrictSummaryRow } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function PublicPage() {
  const { t, num, drug, place } = useI18n();
  const [rows, setRows] = useState<DistrictSummaryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.districtSummary().then(setRows).catch((e) => setError((e as Error).message));
  }, []);

  const reporting = rows?.reduce((a, r) => a + r.facilities_reporting, 0) ?? 0;
  const atRisk = rows?.reduce((a, r) => a + r.facilities_at_risk, 0) ?? 0;
  const byDrug: Record<string, number> = {};
  rows?.forEach((r) => Object.entries(r.at_risk_by_drug).forEach(([d, c]) => (byDrug[d] = (byDrug[d] ?? 0) + c)));
  const drugs = Object.entries(byDrug).sort((a, b) => b[1] - a[1]);

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={t("public_title")} sub={t("public_sub")} />
      {error && <Notice tone="error">{t("error_load", { error })}</Notice>}

      <Reveal className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {rows ? (
          <>
            <Stat label={t("public_col_district")} value={num(rows.length)} />
            <Stat label={t("public_col_reporting")} value={num(reporting)} />
            <Stat label={t("public_col_at_risk")} value={num(atRisk)} hint={reporting ? `${num((100 * atRisk) / reporting)}%` : undefined} tone="risk" />
          </>
        ) : (
          Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-[104px] rounded-xl" />)
        )}
      </Reveal>

      <Reveal delay={0.08} className="card mt-6 overflow-hidden">
        <table className="w-full text-sm" data-testid="public-table">
          <thead className="bg-zinc-50 text-left dark:bg-zinc-800/50">
            <tr>
              <th className="label px-4 py-3 font-medium">{t("public_col_district")}</th>
              <th className="label px-4 py-3 text-right font-medium">{t("public_col_reporting")}</th>
              <th className="label px-4 py-3 text-right font-medium">{t("public_col_at_risk")}</th>
            </tr>
          </thead>
          <tbody>
            {(rows ?? []).map((r) => (
              <tr key={r.district_id} className="border-t border-zinc-100 dark:border-zinc-800">
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2 font-medium">
                    <Buildings size={16} className="text-teal-700 dark:text-teal-400" /> {place(r.district_id)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">{num(r.facilities_reporting)}</td>
                <td className="px-4 py-3 text-right">
                  <span className="inline-flex items-center gap-1 font-medium text-rose-700 dark:text-rose-400">
                    {r.facilities_at_risk > 0 && <Warning size={14} weight="fill" />} {num(r.facilities_at_risk)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>

      {drugs.length > 0 && (
        <Reveal delay={0.14} className="card mt-6 p-5">
          <h2 className="h2 mb-4">{t("public_by_medicine")}</h2>
          <ul className="grid gap-x-8 gap-y-3 md:grid-cols-2">
            {drugs.map(([id, count]) => (
              <li key={id}>
                <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
                  <span className="font-medium">{drug(id)}</span>
                  <span className="muted shrink-0 text-xs">{t("shortage_line", { count: num(count), total: num(reporting) })}</span>
                </div>
                <div
                  className={`h-1.5 rounded-full ${count / reporting > 0.5 ? "bg-rose-500 dark:bg-rose-400" : "bg-amber-400 dark:bg-amber-300"}`}
                  style={{ width: `${Math.max(2, (100 * count) / reporting)}%` }}
                />
              </li>
            ))}
          </ul>
        </Reveal>
      )}
    </div>
  );
}
