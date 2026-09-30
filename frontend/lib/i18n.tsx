"use client";
/**
 * UI language: one dictionary per language in lib/locales (English is the
 * source; the others are type-checked against it). The choice persists in
 * localStorage and is sent to the backend so WhatsApp replies and agent
 * answers come back in the same language. Medicine names come from the
 * backend (/public/drug-names), the single source shared with WhatsApp replies.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import en, { type Messages } from "./locales/en";
import hi from "./locales/hi";
import mr from "./locales/mr";
import bn from "./locales/bn";
import ta from "./locales/ta";
import te from "./locales/te";
import kn from "./locales/kn";
import { api } from "./api";

export const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "mr", label: "मराठी" },
  { code: "bn", label: "বাংলা" },
  { code: "ta", label: "தமிழ்" },
  { code: "te", label: "తెలుగు" },
  { code: "kn", label: "ಕನ್ನಡ" },
] as const;

export type Lang = (typeof LANGS)[number]["code"];
export type MessageKey = keyof Messages;

const DICTS: Record<Lang, Messages> = { en, hi, mr, bn, ta, te, kn };
const STORAGE_KEY = "aushadhinet.lang";

interface I18n {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
  num: (value: number, digits?: number) => string;
  drug: (drugId: string) => string;
  drugIds: string[];
  place: (jurisdiction: string) => string;
  date: (isoDate: string) => string;
}

const Ctx = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  const [drugNames, setDrugNames] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as Lang | null;
      if (saved && saved in DICTS) setLangState(saved);
    } catch {
      /* storage unavailable: stay on English */
    }
    api.drugNames().then(setDrugNames).catch(() => undefined);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<I18n>(() => {
    const dict = DICTS[lang];
    // Latin digits everywhere so UI numbers match the numbers in WhatsApp replies.
    const fmt = new Intl.NumberFormat(`${lang}-IN`, { numberingSystem: "latn" } as Intl.NumberFormatOptions);
    return {
      lang,
      setLang,
      t: (key, vars) => {
        let text = dict[key] ?? en[key];
        for (const [k, v] of Object.entries(vars ?? {})) text = text.replaceAll(`{${k}}`, String(v));
        return text;
      },
      num: (v, digits = 0) =>
        digits ? new Intl.NumberFormat(`${lang}-IN`, { maximumFractionDigits: digits, numberingSystem: "latn" } as Intl.NumberFormatOptions).format(v) : fmt.format(Math.round(v)),
      drug: (id) => drugNames[id]?.[lang] ?? drugNames[id]?.en ?? id,
      drugIds: Object.keys(drugNames),
      date: (iso) => {
        const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
        return Number.isNaN(d.getTime()) ? iso : new Intl.DateTimeFormat(`${lang}-IN`, { day: "numeric", month: "short", year: "numeric", numberingSystem: "latn" } as Intl.DateTimeFormatOptions).format(d);
      },
      place: (jurisdiction) => {
        const slug = jurisdiction.split("/").pop() ?? jurisdiction;
        const key = `place_${slug}` as MessageKey;
        return dict[key] ?? en[key] ?? slug.charAt(0).toUpperCase() + slug.slice(1);
      },
    };
  }, [lang, setLang, drugNames]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}
