"use client";
import { useEffect, useState } from "react";
import { Moon, Sun } from "@phosphor-icons/react";
import { useI18n } from "@/lib/i18n";

export default function ThemeToggle() {
  const { t } = useI18n();
  const [dark, setDark] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
    try {
      localStorage.setItem("aushadhinet.theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
    window.dispatchEvent(new Event("aushadhinet:theme"));
  }

  return (
    <button onClick={toggle} className="rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800" aria-label={t("theme_toggle")} title={t("theme_toggle")}>
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
