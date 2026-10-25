"use client";
/**
 * Beds and staff in the officer's briefing: facilities nearly full with referral suggestions,
 * staff check-ins with deputation suggestions. Suggestions only; the officer arranges them.
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { Bed, UsersThree } from "@phosphor-icons/react";
import { Skeleton } from "@/components/ui";
import { api, Capacity } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function CapacityCard({ district }: { district: string }) {
  const { t, num } = useI18n();
  const [cap, setCap] = useState<Capacity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.capacity(district).then(setCap).catch((e) => setError((e as Error).message));
  }, [district]);

  const time = (minutes: number) => (minutes < 5 ? t("cap_nearby") : t("cap_minutes", { n: num(minutes) }));
  const link = (id: string, name: string) => (
    <Link href={`/facility/${id}`} className="font-medium hover:underline">
      {name}
    </Link>
  );
  // Splits a translated line on its {placeholders} so facility names can be links.
  const line = (key: Parameters<typeof t>[0], parts: Record<string, React.ReactNode>) =>
    t(key, Object.fromEntries(Object.keys(parts).map((k) => [k, `\u0000${k}\u0000`])))
      .split("\u0000")
      .map((chunk, i) => (i % 2 ? <span key={i}>{parts[chunk]}</span> : chunk));

  if (error) return <p className="text-sm text-rose-700 dark:text-rose-400">{t("error_load", { error })}</p>;

  return (
    <section className="card p-5" data-testid="capacity">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h2">{t("cap_title")}</h2>
        {cap?.demo_baseline && <p className="muted max-w-[70ch] text-xs leading-relaxed">{t("cap_demo")}</p>}
      </div>
      {!cap ? (
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <div data-testid="capacity-beds">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <Bed size={18} weight="duotone" className="text-sky-700 dark:text-sky-400" />
              {t("cap_beds", { full: num(cap.beds.full_count), occupied: num(cap.beds.occupied), total: num(cap.beds.total) })}
            </h3>
            <ul className="mt-2 divide-y divide-zinc-100 text-sm dark:divide-zinc-800">
              {cap.beds.referrals.slice(0, 5).map((r) => (
                <li key={`${r.from_id}-${r.to_id}`} className="flex flex-wrap items-baseline justify-between gap-x-3 py-1.5">
                  <span>{line("cap_refer", { from: link(r.from_id, r.from_name), n: num(r.patients), to: link(r.to_id, r.to_name) })}</span>
                  <span className="muted text-xs">{time(r.minutes)}</span>
                </li>
              ))}
              {!cap.beds.referrals.length && <li className="muted py-1.5">{t("cap_none")}</li>}
            </ul>
          </div>
          <div data-testid="capacity-staff">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <UsersThree size={18} weight="duotone" className="text-violet-700 dark:text-violet-400" />
              {t("cap_staff", { present: num(cap.staff.present), rostered: num(cap.staff.rostered) })}
              {cap.staff.nobody_count > 0 && ` · ${t("cap_nobody", { n: num(cap.staff.nobody_count) })}`}
            </h3>
            <ul className="mt-2 divide-y divide-zinc-100 text-sm dark:divide-zinc-800">
              {cap.staff.deputations.slice(0, 3).map((d) => (
                <li key={`${d.role}-${d.from_id}-${d.to_id}`} className="flex flex-wrap items-baseline justify-between gap-x-3 py-1.5">
                  <span>{line("cap_depute", { to: link(d.to_id, d.to_name), n: num(d.staff), role: d.role, from: link(d.from_id, d.from_name) })}</span>
                  <span className="muted text-xs">{time(d.minutes)}</span>
                </li>
              ))}
              {cap.staff.off_site.slice(0, 2).map((c, i) => (
                <li key={`off-${c.facility_id}-${i}`} className="py-1.5 text-amber-800 dark:text-amber-300" data-testid="capacity-off-site">
                  {line("cap_off_site", { name: link(c.facility_id, c.name), role: c.role, km: num(c.distance_m / 1000, 1) })}
                </li>
              ))}
              {!cap.staff.deputations.length && !cap.staff.off_site.length && <li className="muted py-1.5">{t("cap_none")}</li>}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
