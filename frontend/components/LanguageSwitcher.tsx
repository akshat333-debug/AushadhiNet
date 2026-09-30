"use client";
import { Globe } from "@phosphor-icons/react";
import { LANGS, type Lang, useI18n } from "@/lib/i18n";

export default function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();
  return (
    <label className="relative flex items-center">
      <span className="sr-only">{t("language")}</span>
      <Globe size={16} className="pointer-events-none absolute left-2.5 text-zinc-500" />
      <select
        value={lang}
        onChange={(e) => setLang(e.target.value as Lang)}
        className="appearance-none rounded-lg border border-zinc-300 bg-white py-1.5 pl-8 pr-3 text-sm text-zinc-800 hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        data-testid="lang-switcher"
      >
        {LANGS.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}
